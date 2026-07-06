from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

from mcp_server.tools.auth import register_authentication_tools
from mcp_server.tools.credit import register_credit_tools
from mcp_server.tools.exchange import register_exchange_tools
from mcp_server.tools.interview import register_interview_tools
from mcp_server.tools.routing import register_routing_tools
from mcp_server.tools.session import register_session_tools


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        name="banco-agil-mcp-server",
        instructions=(
            "Servidor MCP do Banco Ágil. "
            "Expõe ferramentas de autenticação, crédito, score e câmbio "
            "para consumo pelos agentes de IA."
        ),
    )
    register_authentication_tools(mcp)
    register_routing_tools(mcp)
    register_session_tools(mcp)
    register_credit_tools(mcp)
    register_interview_tools(mcp)
    register_exchange_tools(mcp)
    return mcp


if __name__ == "__main__":
    create_mcp_server().run(transport="stdio")
