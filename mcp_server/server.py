from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

from mcp_server.tools.auth import register_authentication_tools



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
    return mcp


if __name__ == "__main__":
    create_mcp_server().run(transport="stdio")
