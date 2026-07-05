import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt

logger = logging.getLogger(__name__)


class EndConversationSchema(BaseModel):
    reason: str = Field(
        default="",
        description="Motivo do encerramento, se informado pelo cliente.",
    )


@tool(
    description=load_prompt("end_conversation_tool_description.txt"),
    args_schema=EndConversationSchema,
)
def end_conversation(reason: str = "") -> dict:
    logger.info("end_conversation chamada — reason=%s", reason or "(não informado)")
    result = invoke_mcp_tool("end_conversation", {"reason": reason})
    logger.info("end_conversation → ended=%s", result.get("ended"))
    return result
