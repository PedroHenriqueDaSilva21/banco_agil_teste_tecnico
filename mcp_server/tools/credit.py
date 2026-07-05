from mcp.server.fastmcp import FastMCP

from src.services.credit_service import CreditService


def register_credit_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_credit_limit(cpf: str) -> dict:
        credit_service = CreditService()
        success, data, message = credit_service.get_credit_limit(cpf)
        result = {"success": success, "message": message}
        if success:
            result.update(data)
        return result

    @mcp.tool()
    def request_credit_increase(cpf: str, requested_limit: float) -> dict:
        credit_service = CreditService()
        success, data, message = credit_service.request_limit_increase(cpf, requested_limit)
        result = {"success": success, "message": message}
        if data:
            result.update(data)
        return result

    @mcp.tool()
    def redirect_to_interview() -> dict:
        return {
            "redirected": True,
            "target_agent": "interview",
            "message": "Cliente redirecionado para entrevista de crédito.",
        }
