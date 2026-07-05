import logging
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt, mask_cpf

logger = logging.getLogger(__name__)


class SubmitCreditInterviewSchema(BaseModel):
    cpf: str = Field(description="CPF do cliente autenticado.")
    monthly_income: float = Field(ge=0, description="Renda mensal do cliente em reais.")
    job_type: Literal["formal", "autônomo", "desempregado"] = Field(
        description="Tipo de emprego: formal, autônomo ou desempregado."
    )
    monthly_expenses: float = Field(ge=0, description="Despesas fixas mensais em reais.")
    dependents: int = Field(ge=0, description="Número de dependentes.")
    has_debts: bool = Field(description="True se o cliente possui dívidas ativas, False caso contrário.")


@tool(
    description=load_prompt("submit_credit_interview_tool_description.txt"),
    args_schema=SubmitCreditInterviewSchema,
)
def submit_credit_interview(
    cpf: str,
    monthly_income: float,
    job_type: str,
    monthly_expenses: float,
    dependents: int,
    has_debts: bool,
) -> dict:
    logger.info("submit_credit_interview chamada — cpf=%s", mask_cpf(cpf))
    result = invoke_mcp_tool(
        "submit_credit_interview",
        {
            "cpf": cpf,
            "monthly_income": monthly_income,
            "job_type": job_type,
            "monthly_expenses": monthly_expenses,
            "dependents": dependents,
            "has_debts": has_debts,
        },
    )
    logger.info(
        "submit_credit_interview → success=%s new_score=%s",
        result.get("success"),
        result.get("new_score"),
    )
    return result


@tool(description=load_prompt("redirect_to_credit_tool_description.txt"))
def redirect_to_credit() -> dict:
    logger.info("redirect_to_credit chamada")
    result = invoke_mcp_tool("redirect_to_credit", {})
    logger.info("redirect_to_credit → redirected=%s", result.get("redirected"))
    return result
