import logging
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt, mask_cpf
from src.utils.interview_flow import (
    INTERVIEW_FIELD_LABELS,
    parse_interview_field,
)

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


class RecordInterviewAnswerSchema(BaseModel):
    field: Literal[
        "monthly_income",
        "job_type",
        "monthly_expenses",
        "dependents",
        "has_debts",
    ] = Field(description="Campo da entrevista que está sendo registrado.")
    value: str = Field(
        description="Resposta do cliente exatamente como informada, para validação e registro."
    )


@tool(
    description=load_prompt("tools/record_interview_answer_tool_description.txt"),
    args_schema=RecordInterviewAnswerSchema,
)
def record_interview_answer(field: str, value: str) -> dict:
    logger.info("record_interview_answer chamada — field=%s", field)
    parsed, error = parse_interview_field(field, value)
    if error:
        return {"success": False, "message": error}
    return {
        "success": True,
        "field": field,
        "value": parsed,
        "message": f"{INTERVIEW_FIELD_LABELS[field]} registrado com sucesso.",
    }


@tool(
    description=load_prompt("tools/submit_credit_interview_tool_description.txt"),
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


def submit_collected_interview(cpf: str, collected: dict) -> dict:
    return invoke_mcp_tool(
        "submit_credit_interview",
        {
            "cpf": cpf,
            "monthly_income": collected["monthly_income"],
            "job_type": collected["job_type"],
            "monthly_expenses": collected["monthly_expenses"],
            "dependents": collected["dependents"],
            "has_debts": collected["has_debts"],
        },
    )


@tool(description=load_prompt("tools/redirect_to_credit_tool_description.txt"))
def redirect_to_credit() -> dict:
    logger.info("redirect_to_credit chamada")
    result = invoke_mcp_tool("redirect_to_credit", {})
    logger.info("redirect_to_credit → redirected=%s", result.get("redirected"))
    return result
