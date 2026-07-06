import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.agents.credit import create_credit_agent
from src.agents.exchange import create_exchange_agent
from src.agents.interview import create_interview_agent
from src.agents.state import AgentState, initial_agent_state
from src.agents.triage import create_triage_agent

logger = logging.getLogger(__name__)


def create_supervisor():
    triage = create_triage_agent()
    credit = create_credit_agent()
    interview = create_interview_agent()
    exchange = create_exchange_agent()

    agents = {
        "triage": triage,
        "credit": credit,
        "interview": interview,
        "exchange": exchange,
    }

    def _invoke_agent(agent_name: str, state: AgentState, config: RunnableConfig) -> dict:
        logger.info(
            "Supervisor: executando agente %s.",
            agent_name,
            extra={"thread_id": (config or {}).get("configurable", {}).get("thread_id", "-")},
        )
        return agents[agent_name].invoke(state, config)

    def supervisor_node(state: AgentState, config: RunnableConfig) -> dict:
        tid = (config or {}).get("configurable", {}).get("thread_id", "-")

        if state.get("conversation_ended"):
            logger.info("Supervisor: atendimento encerrado.", extra={"thread_id": tid})
            return {}

        current_state = state
        current_target = state.get("target_agent") or "triage"
        last_result: dict = {}
        max_hops = 4

        for hop in range(max_hops):
            if current_target not in agents:
                logger.info(
                    "Supervisor: agente inválido '%s', encerrando cascata.",
                    current_target,
                    extra={"thread_id": tid},
                )
                break

            if hop == 0 and current_target == "triage":
                logger.info("Supervisor: delegando para agente de triagem.", extra={"thread_id": tid})

            result = _invoke_agent(current_target, current_state, config)
            last_result = result

            if result.get("conversation_ended"):
                break

            next_target = result.get("target_agent")
            if not next_target or next_target == current_target:
                break

            logger.info(
                "Supervisor: redirecionamento implícito %s -> %s.",
                current_target,
                next_target,
                extra={"thread_id": tid},
            )
            # Ao entrar no agente de entrevista vindo de outro agente,
            # garante que o estado da entrevista está limpo para evitar
            # que dados de sessões anteriores contaminem a nova entrevista.
            if next_target == "interview" and current_target != "interview":
                logger.info(
                    "Supervisor: resetando estado da entrevista antes de iniciar.",
                    extra={"thread_id": tid},
                )
                result["interview_opening_delivered"] = False
                result["interview_collected"] = {}
                result["interview_submitted"] = False
                result["interview_await_user"] = False
            current_state = result
            current_target = next_target

        return last_result

    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", END)

    return graph.compile()


supervisor_agent = create_supervisor()

__all__ = ["create_supervisor", "supervisor_agent", "initial_agent_state"]
