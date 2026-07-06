import json
import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.agents.state import AgentState, parse_tool_payload
from src.config.settings import settings
from src.tools.interview import record_interview_answer, submit_collected_interview
from src.tools.session import end_conversation
from src.utils import load_prompt, sanitize_input
from src.utils.interview_flow import (
    INTERVIEW_FIELD_LABELS,
    INTERVIEW_OPENING,
    INTERVIEW_QUESTIONS,
    interview_fields_complete,
    next_interview_field,
)

logger = logging.getLogger(__name__)

_tools = [record_interview_answer, end_conversation]
_INTERVIEW_SYSTEM_PROMPT = load_prompt("agents/interview.md")
_BLOCKED_MESSAGE = (
    "Não foi possível processar sua mensagem. "
    "Por favor, utilize apenas texto simples para interagir com o atendimento."
)


def _build_system_prompt(state: AgentState) -> str:
    collected = state.get("interview_collected") or {}
    context_lines = [
        "",
        "## Dados do cliente autenticado",
        f"- Nome: {state.get('customer_name') or 'N/A'}",
        f"- CPF: {state.get('customer_cpf') or 'N/A'}",
        f"- Score atual: {state.get('customer_score') or 'N/A'}",
        f"- Limite atual: {state.get('customer_limit') or 'N/A'}",
        "",
        "## Progresso da entrevista",
        f"- Dados coletados: {collected or 'nenhum'}",
    ]

    if state.get("interview_submitted"):
        context_lines.append("- Entrevista já registrada. Não chame ferramentas de registro.")
    elif not state.get("interview_opening_delivered"):
        context_lines.append(
            "- A abertura da entrevista será feita automaticamente. Aguarde a próxima interação."
        )
    else:
        current_field = next_interview_field(collected)
        if current_field:
            context_lines.extend(
                [
                    f"- Campo atual a registrar: **{current_field}** ({INTERVIEW_FIELD_LABELS[current_field]})",
                    "- Quando o cliente responder, chame `record_interview_answer` com esse campo.",
                    "- Não chame `submit_credit_interview` nem `redirect_to_credit`.",
                ]
            )

    return _INTERVIEW_SYSTEM_PROMPT + "\n".join(context_lines)


def _format_score_message(payload: dict) -> str:
    previous = payload.get("previous_score")
    new_score = payload.get("new_score")
    return (
        "Entrevista registrada com sucesso!\n\n"
        f"- Score anterior: **{previous}**\n"
        f"- Novo score: **{new_score:.0f}**\n\n"
        "Vou prosseguir com uma nova análise de limite de crédito para você."
    )


def _route_after_agent(state: AgentState) -> str:
    if state.get("conversation_ended") or state.get("interview_submitted"):
        return END

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"

    if state.get("interview_await_user"):
        return END

    return END


def _apply_tool_side_effects(
    state: AgentState,
    tool_messages: list[ToolMessage],
) -> dict:
    conversation_ended = state.get("conversation_ended", False)
    customer_score = state.get("customer_score")
    target_agent = state.get("target_agent", "interview")
    returned_from_interview = state.get("returned_from_interview", False)
    last_request_status = state.get("last_request_status")
    interview_offered = state.get("interview_offered", False)
    interview_collected = dict(state.get("interview_collected") or {})
    interview_submitted = state.get("interview_submitted", False)
    interview_await_user = state.get("interview_await_user", False)
    extra_messages: list[AIMessage] = []

    for msg in tool_messages:
        payload = parse_tool_payload(msg.content)

        if msg.name == "record_interview_answer":
            if not payload.get("success"):
                interview_await_user = False
                continue

            field = payload.get("field")
            expected_field = next_interview_field(interview_collected)
            if field != expected_field:
                continue

            interview_collected[field] = payload.get("value")
            interview_await_user = False

            if interview_fields_complete(interview_collected):
                submit_payload = submit_collected_interview(
                    state.get("customer_cpf", ""),
                    interview_collected,
                )
                if submit_payload.get("success"):
                    interview_submitted = True
                    customer_score = submit_payload.get("new_score", customer_score)
                    target_agent = "credit"
                    returned_from_interview = True
                    last_request_status = None
                    interview_offered = False
                    extra_messages.append(AIMessage(content=_format_score_message(submit_payload)))
                else:
                    extra_messages.append(
                        AIMessage(
                            content=(
                                submit_payload.get("message")
                                or "Não foi possível registrar a entrevista. Tente novamente."
                            )
                        )
                    )
                    interview_await_user = True
            else:
                next_field = next_interview_field(interview_collected)
                if next_field:
                    extra_messages.append(AIMessage(content=INTERVIEW_QUESTIONS[next_field]))
                    interview_await_user = True

        elif msg.name == "end_conversation" and payload.get("ended"):
            conversation_ended = True

    return {
        "customer_score": customer_score,
        "target_agent": target_agent,
        "returned_from_interview": returned_from_interview,
        "last_request_status": last_request_status,
        "interview_offered": interview_offered,
        "conversation_ended": conversation_ended,
        "interview_collected": interview_collected,
        "interview_submitted": interview_submitted,
        "interview_await_user": interview_await_user,
        "extra_messages": extra_messages,
    }


def create_interview_agent():
    llm = ChatBedrockConverse(
        model_id=settings.bedrock_llm_model,
        region_name=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    llm_with_tools = llm.bind_tools(_tools)

    def sanitize_node(state: AgentState) -> dict:
        if state.get("conversation_ended"):
            return {}

        raw_input = state.get("pending_user_input")

        if raw_input is None:
            return {}

        clean = sanitize_input(raw_input)
        if clean is None:
            logger.warning("Entrada bloqueada pelo sanitizador — mensagem descartada.")
            return {
                "messages": [AIMessage(content=_BLOCKED_MESSAGE)],
                "pending_user_input": None,
                "input_blocked": True,
            }
        return {
            "messages": [HumanMessage(content=clean)],
            "pending_user_input": None,
            "input_blocked": False,
            "interview_await_user": False,
        }

    def prepare_node(state: AgentState) -> dict:
        if state.get("interview_opening_delivered"):
            return {}

        first_name = (state.get("customer_name") or "cliente").split()[0]
        return {
            "interview_started": True,
            "interview_opening_delivered": True,
            "interview_await_user": True,
            "interview_collected": {},      # garante início limpo a cada nova entrevista
            "interview_submitted": False,   # garante que não herdamos submitted=True
            "target_agent": "interview",
            "messages": [AIMessage(content=INTERVIEW_OPENING.format(first_name=first_name))],
        }

    def after_sanitize(state: AgentState) -> str:
        if state.get("conversation_ended"):
            return END
        return END if state.get("input_blocked") else "prepare"

    def after_prepare(state: AgentState) -> str:
        if state.get("conversation_ended") or state.get("interview_submitted"):
            return END
        if state.get("interview_await_user") and state.get("pending_user_input") is None:
            return END
        return "agent"

    def call_llm(state: AgentState, config: RunnableConfig) -> dict:
        if state.get("interview_submitted"):
            return {}

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
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", None) or []
        tool_messages: list[ToolMessage] = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            if tool_name == "record_interview_answer":
                expected_field = next_interview_field(state.get("interview_collected") or {})
                requested_field = tool_args.get("field")
                if requested_field != expected_field:
                    payload = {
                        "success": False,
                        "message": (
                            f"Registre primeiro o campo '{expected_field}' "
                            f"({INTERVIEW_FIELD_LABELS.get(expected_field, expected_field)})."
                            if expected_field
                            else "Entrevista já concluída."
                        ),
                    }
                else:
                    payload = record_interview_answer.invoke(tool_args)
            elif tool_name == "end_conversation":
                payload = end_conversation.invoke(tool_args)
            else:
                payload = {"success": False, "message": f"Ferramenta não permitida: {tool_name}."}

            tool_messages.append(
                ToolMessage(
                    content=json.dumps(payload, ensure_ascii=False),
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            )

        side_effects = _apply_tool_side_effects(state, tool_messages)
        extra_messages = side_effects.pop("extra_messages", [])
        updates = {"messages": tool_messages + extra_messages}
        updates.update(side_effects)
        return updates

    def after_tools(state: AgentState) -> str:
        if state.get("conversation_ended") or state.get("interview_submitted"):
            return END
        if state.get("interview_await_user"):
            return END
        return "agent"

    graph = StateGraph(AgentState)
    graph.add_node("sanitize", sanitize_node)
    graph.add_node("prepare", prepare_node)
    graph.add_node("agent", call_llm)
    graph.add_node("tools", process_tools)

    graph.add_edge(START, "sanitize")
    graph.add_conditional_edges("sanitize", after_sanitize, {"prepare": "prepare", END: END})
    graph.add_conditional_edges("prepare", after_prepare, {"agent": "agent", END: END})
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", END: END})
    graph.add_conditional_edges("tools", after_tools, {"agent": "agent", END: END})

    return graph.compile()


interview_agent = create_interview_agent()
