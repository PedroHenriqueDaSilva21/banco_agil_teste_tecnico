import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.state import initial_agent_state


def make_tool_call_response(tool_name: str, tool_args: dict, tool_call_id: str = "call_1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": tool_name,
                "args": tool_args,
                "id": tool_call_id,
                "type": "tool_call",
            }
        ],
    )


def make_text_response(text: str) -> AIMessage:
    return AIMessage(content=text)


@pytest.fixture
def authenticated_credit_state():
    state = initial_agent_state([HumanMessage(content="qual meu limite?")])
    state.update(
        {
            "authenticated": True,
            "customer_cpf": "12345678901",
            "customer_name": "Ana Silva",
            "customer_score": 629.0,
            "customer_limit": 2500.0,
            "target_agent": "credit",
            "intent": "CREDIT_LIMIT",
        }
    )
    return state


@pytest.fixture
def authenticated_exchange_state():
    state = initial_agent_state([HumanMessage(content="qual a cotação do dólar?")])
    state.update(
        {
            "authenticated": True,
            "customer_cpf": "12345678901",
            "customer_name": "Ana Silva",
            "target_agent": "exchange",
            "intent": "EXCHANGE",
        }
    )
    return state


@pytest.fixture
def authenticated_interview_state():
    state = initial_agent_state([HumanMessage(content="sim, quero fazer a entrevista")])
    state.update(
        {
            "authenticated": True,
            "customer_cpf": "12345678901",
            "customer_name": "Ana Silva",
            "customer_score": 250.0,
            "customer_limit": 2500.0,
            "target_agent": "interview",
            "last_request_status": "rejeitado",
            "interview_offered": True,
        }
    )
    return state
