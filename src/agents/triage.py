import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.agents.state import AgentState, parse_tool_payload
from src.config.settings import settings
from src.tools import authenticate_customer, classify_intent, end_conversation
from src.utils import load_prompt, sanitize_input

logger = logging.getLogger(__name__)

MAX_AUTH_ATTEMPTS = 3
_tools = [authenticate_customer, classify_intent, end_conversation]
_TRIAGE_SYSTEM_PROMPT = load_prompt("agents/triage.md")
_BLOCKED_MESSAGE = (
    "Não foi possível processar sua mensagem. "
    "Por favor, utilize apenas texto simples para interagir com o atendimento."
)
_AUTH_LOCKOUT_MESSAGE = (
    "Infelizmente não conseguimos validar seus dados após várias tentativas. "
    "Por segurança, precisamos encerrar este atendimento. "
    "Por favor, entre em contato novamente ou visite uma agência do Banco Ágil."
)


def _route_after_agent(state: AgentState) -> str:
    if state.get("conversation_ended"):
        return END

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END


def _apply_tool_side_effects(
    state: AgentState,
    tool_messages: list[ToolMessage],
) -> dict:
    auth_attempts = state.get("auth_attempts", 0)
    authenticated = state.get("authenticated", False)
    conversation_ended = state.get("conversation_ended", False)
    customer_cpf = state.get("customer_cpf")
    customer_name = state.get("customer_name")
    customer_score = state.get("customer_score")
    customer_limit = state.get("customer_limit")
    target_agent = state.get("target_agent")
    intent = state.get("intent")
    extra_messages: list[AIMessage] = []

    for msg in tool_messages:
        payload = parse_tool_payload(msg.content)

        if msg.name == "authenticate_customer":
            if payload.get("success"):
                authenticated = True
                customer_cpf = payload.get("customer_cpf")
                customer_name = payload.get("customer_name")
                customer_score = payload.get("customer_score")
                customer_limit = payload.get("customer_limit")
            else:
                auth_attempts += 1
                if auth_attempts >= MAX_AUTH_ATTEMPTS:
                    conversation_ended = True
                    extra_messages.append(AIMessage(content=_AUTH_LOCKOUT_MESSAGE))

        elif msg.name == "classify_intent":
            if payload.get("target_agent"):
                target_agent = payload.get("target_agent")
                intent = payload.get("intent")

        elif msg.name == "end_conversation":
            if payload.get("ended"):
                conversation_ended = True

    return {
        "auth_attempts": auth_attempts,
        "authenticated": authenticated,
        "customer_cpf": customer_cpf,
        "customer_name": customer_name,
        "customer_score": customer_score,
        "customer_limit": customer_limit,
        "target_agent": target_agent,
        "intent": intent,
        "conversation_ended": conversation_ended,
        "extra_messages": extra_messages,
    }


def create_triage_agent():
    llm = ChatBedrockConverse(
        model_id=settings.bedrock_llm_model,
        region_name=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    llm_with_tools = llm.bind_tools(_tools)
    tool_node = ToolNode(_tools)

    def sanitize_node(state: AgentState) -> dict:
        if state.get("conversation_ended"):
            return {}

        raw_input = state.get("pending_user_input")

        if raw_input is None:
            return {}

        clean = sanitize_input(raw_input)
        if clean is None:
            logger.warning("Entrada bloqueada pelo sanitizador — mensagem descartada.")
            return {"messages": [AIMessage(content=_BLOCKED_MESSAGE)], "pending_user_input": None, "input_blocked": True}
        return {"messages": [HumanMessage(content=clean)], "pending_user_input": None, "input_blocked": False}

    def after_sanitize(state: AgentState) -> str:
        if state.get("conversation_ended"):
            return END
        return END if state.get("input_blocked") else "agent"

    def call_llm(state: AgentState, config: RunnableConfig) -> dict:
        tid = (config or {}).get("configurable", {}).get("thread_id", "-")
        num_msgs = len(state.get("messages", []))
        logger.info(
            "Invocando LLM — histórico: %d msgs | autenticado=%s | tentativas=%d",
            num_msgs,
            state.get("authenticated", False),
            state.get("auth_attempts", 0),
            extra={"thread_id": tid},
        )
        try:
            system_message = SystemMessage(content=_TRIAGE_SYSTEM_PROMPT)
            response = llm_with_tools.invoke([system_message] + state["messages"])

            if getattr(response, "tool_calls", None):
                tool_names = ", ".join(tc["name"] for tc in response.tool_calls)
                logger.info(
                    "LLM solicitou tool(s): %s",
                    tool_names,
                    extra={"thread_id": tid},
                )
            else:
                logger.info("LLM retornou resposta final.", extra={"thread_id": tid})

            return {"messages": [response]}
        except Exception as exc:
            logger.error(
                "Falha na comunicação com o LLM: %s",
                exc,
                exc_info=True,
                extra={"thread_id": tid},
            )
            raise

    def process_tools(state: AgentState) -> dict:
        tool_result = tool_node.invoke(state)
        tool_messages = [
            msg for msg in tool_result["messages"] if isinstance(msg, ToolMessage)
        ]
        side_effects = _apply_tool_side_effects(state, tool_messages)

        extra_messages = side_effects.pop("extra_messages", [])
        updates = {"messages": tool_result["messages"] + extra_messages}
        updates.update(side_effects)
        return updates

    def after_tools(state: AgentState) -> str:
        if state.get("conversation_ended") and state.get("auth_attempts", 0) >= MAX_AUTH_ATTEMPTS:
            return END
        return "agent"

    graph = StateGraph(AgentState)
    graph.add_node("sanitize", sanitize_node)
    graph.add_node("agent", call_llm)
    graph.add_node("tools", process_tools)

    graph.add_edge(START, "sanitize")
    graph.add_conditional_edges("sanitize", after_sanitize, {"agent": "agent", END: END})
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", END: END})
    graph.add_conditional_edges("tools", after_tools, {"agent": "agent", END: END})

    return graph.compile()


triage_agent = create_triage_agent()
