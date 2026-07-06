from mcp.server.fastmcp import FastMCP

from src.services.routing import RoutingService


def register_routing_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def classify_intent(user_message: str) -> dict:
        routing_service = RoutingService()
        return routing_service.classify_intent(user_message)
