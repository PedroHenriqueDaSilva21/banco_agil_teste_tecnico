from mcp.server.fastmcp import FastMCP

from src.models import CreditInterview
from src.services.interview_service import InterviewService


def register_interview_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def submit_credit_interview(
        cpf: str,
        monthly_income: float,
        job_type: str,
        monthly_expenses: float,
        dependents: int,
        has_debts: bool,
    ) -> dict:
        interview_service = InterviewService()
        interview = CreditInterview(
            monthly_income=monthly_income,
            job_type=job_type,
            monthly_expenses=monthly_expenses,
            dependents=dependents,
            has_debts=has_debts,
        )
        success, data, message = interview_service.submit_interview(cpf, interview)
        result = {"success": success, "message": message}
        if success:
            result.update(data)
        return result

    @mcp.tool()
    def redirect_to_credit() -> dict:
        return {
            "redirected": True,
            "target_agent": "credit",
            "message": "Cliente redirecionado para análise de crédito.",
        }
