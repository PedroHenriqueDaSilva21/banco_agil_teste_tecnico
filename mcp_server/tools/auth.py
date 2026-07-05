from mcp.server.fastmcp import FastMCP

from src.services import AuthService


def register_authentication_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def authenticate_customer(cpf: str, birth_date: str) -> dict:
        auth_service = AuthService()
        success, customer, message = auth_service.authenticate(cpf, birth_date)

        result = {"success": success, "message": message}
        if success and customer:
            result["customer_name"] = customer.name

        return result