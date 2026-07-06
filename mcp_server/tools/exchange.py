from mcp.server.fastmcp import FastMCP

from src.services.exchange_service import ExchangeService


def register_exchange_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_currency_quote(currency: str = "USD") -> dict:
        exchange_service = ExchangeService()
        success, data, message = exchange_service.get_quote(currency)
        result = {"success": success, "message": message}
        if success:
            result.update(data)
        return result
