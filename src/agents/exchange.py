import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.agents.state import AgentState, parse_tool_payload
from src.config.settings import settings
from src.tools.exchange import get_currency_quote
from src.tools.session import end_conversation
from src.utils import load_prompt, sanitize_input

logger = logging.getLogger(__name__)

_tools = [get_currency_quote, end_conversation]
_EXCHANGE_SYSTEM_PROMPT = load_prompt("exchange.md")
_BLOCKED_MESSAGE = (
    "Não foi possível processar sua mensagem. "
    "Por favor, utilize apenas texto simples para interagir com o atendimento."
)


def _build_system_prompt(state: AgentState) -> str:
    context_lines = [
        "",
        "## Dados do cliente autenticado",
        f"- Nome: {state.get('customer_name') or 'N/A'}",
        f"- Intenção identificada: {state.get('intent') or 'N/A'}",
    ]
    return _EXCHANGE_SYSTEM_PROMPT + "\n".join(context_lines)


def _route_after_agent(state: AgentState) -> str:
    if state.get("conversation_ended"):
        return END

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"

    if state.get("quote_delivered"):
        return "finalize"

    return END


def _apply_tool_side_effects(
    state: AgentState,
    tool_messages: list[ToolMessage],
) -> dict:
    conversation_ended = state.get("conversation_ended", False)
    quote_delivered = state.get("quote_delivered", False)

    for msg in tool_messages:
        payload = parse_tool_payload(msg.content)

        if msg.name == "end_conversation" and payload.get("ended"):
            conversation_ended = True
        elif msg.name == "get_currency_quote" and payload.get("success"):
            quote_delivered = True

    return {
        "conversation_ended": conversation_ended,
        "quote_delivered": quote_delivered,
    }


def create_exchange_agent():
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

        last_message = state["messages"][-1]
        clean = sanitize_input(last_message.content)
        if clean is None:
            logger.warning("Entrada bloqueada pelo sanitizador — mensagem descartada.")
            return {"messages": [AIMessage(content=_BLOCKED_MESSAGE)]}
        return {"messages": [HumanMessage(content=clean)]}

    def after_sanitize(state: AgentState) -> str:
        if state.get("conversation_ended"):
            return END
        last_message = state["messages"][-1]
        return END if isinstance(last_message, AIMessage) else "agent"

    def call_llm(state: AgentState, config: RunnableConfig) -> dict:
        tid = (config or {}).get("configurable", {}).get("thread_id", "-")
        logger.info(
            "Agente de câmbio — invocando LLM | intent=%s",
            state.get("intent"),
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
                "Falha na comunicação com o LLM (câmbio): %s",
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

    def finalize_exchange(state: AgentState) -> dict:
        if state.get("conversation_ended"):
            return {}
        logger.info("Cotação entregue — encerrando atendimento de câmbio.")
        return {"conversation_ended": True}

    graph = StateGraph(AgentState)
    graph.add_node("sanitize", sanitize_node)
    graph.add_node("agent", call_llm)
    graph.add_node("tools", process_tools)
    graph.add_node("finalize", finalize_exchange)

    graph.add_edge(START, "sanitize")
    graph.add_conditional_edges("sanitize", after_sanitize, {"agent": "agent", END: END})
    graph.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"tools": "tools", "finalize": "finalize", END: END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    return graph.compile()


exchange_agent = create_exchange_agent()
