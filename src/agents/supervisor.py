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

    def supervisor_node(state: AgentState, config: RunnableConfig) -> dict:
        tid = (config or {}).get("configurable", {}).get("thread_id", "-")

        if state.get("conversation_ended"):
            logger.info("Supervisor: atendimento encerrado.", extra={"thread_id": tid})
            return {}

        target = state.get("target_agent")
        if target == "credit":
            logger.info("Supervisor: roteando para agente de crédito.", extra={"thread_id": tid})
            return credit.invoke(state, config)
        if target == "interview":
            logger.info("Supervisor: roteando para entrevista de crédito.", extra={"thread_id": tid})
            return interview.invoke(state, config)
        if target == "exchange":
            logger.info("Supervisor: roteando para agente de câmbio.", extra={"thread_id": tid})
            return exchange.invoke(state, config)

        logger.info("Supervisor: delegando para agente de triagem.", extra={"thread_id": tid})
        return triage.invoke(state, config)

    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", END)

    return graph.compile()


supervisor_agent = create_supervisor()

__all__ = ["create_supervisor", "supervisor_agent", "initial_agent_state"]
