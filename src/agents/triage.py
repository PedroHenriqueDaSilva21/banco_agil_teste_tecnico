

import logging


from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


from src.config.settings import settings
from src.tools import authenticate_customer
from src.utils import load_prompt, sanitize_input

logger = logging.getLogger(__name__)


_tools = [authenticate_customer]
_TRIAGE_SYSTEM_PROMPT = load_prompt("triage.md")
_BLOCKED_MESSAGE = (
    "Não foi possível processar sua mensagem. "
    "Por favor, utilize apenas texto simples para interagir com o atendimento."
)


def create_triage_agent():

    llm = ChatBedrockConverse(
        model_id=settings.bedrock_llm_model,
        region_name=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    llm_with_tools = llm.bind_tools(_tools)


    def sanitize_node(state: MessagesState) -> dict:
        last_message = state["messages"][-1]
        clean = sanitize_input(last_message.content)
        if clean is None:
            logger.warning("Entrada bloqueada pelo sanitizador — mensagem descartada.")
            return {"messages": [AIMessage(content=_BLOCKED_MESSAGE)]}
        return {"messages": [HumanMessage(content=clean)]}

    def after_sanitize(state: MessagesState) -> str:
        last_message = state["messages"][-1]
        return END if isinstance(last_message, AIMessage) else "agent"

    def call_llm(state: MessagesState, config: RunnableConfig) -> dict:
        tid = (config or {}).get("configurable", {}).get("thread_id", "-")
        num_msgs = len(state.get("messages", []))
        logger.info(
            "Invocando LLM — histórico: %d msgs",
            num_msgs,
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


    tool_node = ToolNode(_tools)

    graph = StateGraph(MessagesState)
    graph.add_node("sanitize", sanitize_node)
    graph.add_node("agent", call_llm)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "sanitize")
    graph.add_conditional_edges("sanitize", after_sanitize, {"agent": "agent", END: END})
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    graph.add_edge("agent", END)

    return graph.compile()


triage_agent = create_triage_agent()
