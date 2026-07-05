import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt, mask_cpf, mask_date

logger = logging.getLogger(__name__)


class AuthenticateCustomerSchema(BaseModel):
    cpf: str = Field(
        description="O CPF do cliente (apenas números ou formatado com pontos e traço)."
    )
    birth_date: str = Field(
        description="A data de nascimento do cliente (aceita DD/MM/YYYY ou YYYY-MM-DD)."
    )


@tool(
    description=load_prompt("auth_tool_description.txt"),
    args_schema=AuthenticateCustomerSchema,
)
def authenticate_customer(cpf: str, birth_date: str) -> dict:
    logger.info(
        "authenticate_customer chamada — cpf=%s nascimento=%s",
        mask_cpf(cpf),
        mask_date(birth_date),
    )

    result = invoke_mcp_tool(
        "authenticate_customer",
        {"cpf": cpf, "birth_date": birth_date},
    )

    status = "OK" if result.get("success") else "FAIL"
    logger.info(
        "authenticate_customer → %s: %s",
        status,
        result.get("message", ""),
    )
    return result
