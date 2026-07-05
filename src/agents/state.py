import json
from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    auth_attempts: int
    authenticated: bool
    customer_cpf: Optional[str]
    customer_name: Optional[str]
    customer_score: Optional[float]
    customer_limit: Optional[float]
    target_agent: Optional[str]
    intent: Optional[str]
    conversation_ended: bool
    last_request_status: Optional[str]
    interview_offered: bool


def initial_agent_state(messages: list | None = None) -> AgentState:
    return {
        "messages": messages or [],
        "auth_attempts": 0,
        "authenticated": False,
        "customer_cpf": None,
        "customer_name": None,
        "customer_score": None,
        "customer_limit": None,
        "target_agent": None,
        "intent": None,
        "conversation_ended": False,
        "last_request_status": None,
        "interview_offered": False,
    }


def parse_tool_payload(content) -> dict:
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return {}
