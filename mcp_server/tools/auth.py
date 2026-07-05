from mcp.server.fastmcp import FastMCP

from src.services import AuthService


def register_authentication_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def authenticate_customer(cpf: str, birth_date: str) -> dict:
        auth_service = AuthService()
        success, customer, message = auth_service.authenticate(cpf, birth_date)

        result = {"success": success, "message": message}
        if success and customer:
            result.update(
                {
                    "customer_name": customer.name,
                    "customer_cpf": customer.cpf,
                    "customer_score": customer.score,
                    "customer_limit": customer.current_limit,
                }
            )

        return result