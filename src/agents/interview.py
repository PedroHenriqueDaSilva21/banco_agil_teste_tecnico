import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.agents.state import AgentState, parse_tool_payload
from src.config.settings import settings
from src.tools.interview import redirect_to_credit, submit_credit_interview
from src.tools.session import end_conversation
from src.utils import load_prompt, sanitize_input

logger = logging.getLogger(__name__)

_tools = [submit_credit_interview, redirect_to_credit, end_conversation]
_INTERVIEW_SYSTEM_PROMPT = load_prompt("agents/interview.md")
_BLOCKED_MESSAGE = (
    "Não foi possível processar sua mensagem. "
    "Por favor, utilize apenas texto simples para interagir com o atendimento."
)


def _build_system_prompt(state: AgentState) -> str:
    context_lines = [
        "",
        "## Dados do cliente autenticado",
        f"- Nome: {state.get('customer_name') or 'N/A'}",
        f"- CPF: {state.get('customer_cpf') or 'N/A'}",
        f"- Score atual: {state.get('customer_score') or 'N/A'}",
        f"- Limite atual: {state.get('customer_limit') or 'N/A'}",
    ]
    return _INTERVIEW_SYSTEM_PROMPT + "\n".join(context_lines)


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
    conversation_ended = state.get("conversation_ended", False)
    customer_score = state.get("customer_score")
    target_agent = state.get("target_agent")
    returned_from_interview = state.get("returned_from_interview", False)
    last_request_status = state.get("last_request_status")
    interview_offered = state.get("interview_offered", False)

    for msg in tool_messages:
        payload = parse_tool_payload(msg.content)

        if msg.name == "submit_credit_interview" and payload.get("success"):
            customer_score = payload.get("new_score", customer_score)

        elif msg.name == "redirect_to_credit" and payload.get("redirected"):
            target_agent = payload.get("target_agent", "credit")
            returned_from_interview = True
            last_request_status = None
            interview_offered = False

        elif msg.name == "end_conversation" and payload.get("ended"):
            conversation_ended = True

    return {
        "customer_score": customer_score,
        "target_agent": target_agent,
        "returned_from_interview": returned_from_interview,
        "last_request_status": last_request_status,
        "interview_offered": interview_offered,
        "conversation_ended": conversation_ended,
    }


def create_interview_agent():
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
        logger.info(
            "Agente de entrevista — invocando LLM | cpf=%s | score=%s",
            state.get("customer_cpf"),
            state.get("customer_score"),
            extra={"thread_id": tid},
        )
        try:
            system_message = SystemMessage(content=_build_system_prompt(state))
            response = llm_with_tools.invoke([system_message] + state["messages"])

            if getattr(response, "tool_calls", None):
                tool_names = ", ".join(tc["name"] for tc in response.tool_calls)
                logger.info(
                    "LLM solicitou tool(s): %s",
                    tool_names,
                    extra={"thread_id": tid},
                )

            return {"messages": [response]}
        except Exception as exc:
            logger.error(
                "Falha na comunicação com o LLM (entrevista): %s",
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
        return {"messages": tool_result["messages"], **side_effects}

    graph = StateGraph(AgentState)
    graph.add_node("sanitize", sanitize_node)
    graph.add_node("agent", call_llm)
    graph.add_node("tools", process_tools)

    graph.add_edge(START, "sanitize")
    graph.add_conditional_edges("sanitize", after_sanitize, {"agent": "agent", END: END})
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


interview_agent = create_interview_agent()
