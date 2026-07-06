from mcp.server.fastmcp import FastMCP

from src.services.session_service import SessionService


def register_session_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def end_conversation(reason: str = "") -> dict:
        session_service = SessionService()
        return session_service.end_conversation(reason)
