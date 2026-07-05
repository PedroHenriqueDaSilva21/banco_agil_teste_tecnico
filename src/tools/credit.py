import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt, mask_cpf

logger = logging.getLogger(__name__)


class GetCreditLimitSchema(BaseModel):
    cpf: str = Field(description="CPF do cliente autenticado.")


@tool(
    description=load_prompt("get_credit_limit_tool_description.txt"),
    args_schema=GetCreditLimitSchema,
)
def get_credit_limit(cpf: str) -> dict:
    logger.info("get_credit_limit chamada — cpf=%s", mask_cpf(cpf))
    result = invoke_mcp_tool("get_credit_limit", {"cpf": cpf})
    logger.info("get_credit_limit → success=%s", result.get("success"))
    return result


class RequestCreditIncreaseSchema(BaseModel):
    cpf: str = Field(description="CPF do cliente autenticado.")
    requested_limit: float = Field(description="Novo limite de crédito desejado pelo cliente.")


@tool(
    description=load_prompt("request_credit_increase_tool_description.txt"),
    args_schema=RequestCreditIncreaseSchema,
)
def request_credit_increase(cpf: str, requested_limit: float) -> dict:
    logger.info(
        "request_credit_increase chamada — cpf=%s limite=%.2f",
        mask_cpf(cpf),
        requested_limit,
    )
    result = invoke_mcp_tool(
        "request_credit_increase",
        {"cpf": cpf, "requested_limit": requested_limit},
    )
    logger.info(
        "request_credit_increase → success=%s status=%s",
        result.get("success"),
        result.get("status"),
    )
    return result


@tool(description=load_prompt("redirect_to_interview_tool_description.txt"))
def redirect_to_interview() -> dict:
    logger.info("redirect_to_interview chamada")
    result = invoke_mcp_tool("redirect_to_interview", {})
    logger.info("redirect_to_interview → redirected=%s", result.get("redirected"))
    return result
