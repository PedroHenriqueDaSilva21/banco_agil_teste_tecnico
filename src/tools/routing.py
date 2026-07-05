import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt, mask_cpf, mask_date

logger = logging.getLogger(__name__)


class ClassifyIntentSchema(BaseModel):
    user_message: str = Field(
        description="Mensagem do cliente descrevendo o serviço desejado após autenticação."
    )


@tool(
    description=load_prompt("tools/classify_intent_tool_description.txt"),
    args_schema=ClassifyIntentSchema,
)
def classify_intent(user_message: str) -> dict:
    logger.info("classify_intent chamada — msg=%d chars", len(user_message))
    result = invoke_mcp_tool("classify_intent", {"user_message": user_message})
    logger.info(
        "classify_intent → intent=%s target=%s",
        result.get("intent"),
        result.get("target_agent"),
    )
    return result
