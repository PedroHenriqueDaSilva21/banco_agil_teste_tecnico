import asyncio
import json
import logging
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=dict(os.environ),
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.call_tool(tool_name, arguments)

            if not response.content:
                return {"success": False, "message": "Sem resposta do servidor MCP."}

            raw = response.content[0].text
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                import ast

                try:
                    return ast.literal_eval(raw)
                except Exception:
                    return {"success": False, "message": f"Resposta inesperada do MCP: {raw}"}


def invoke_mcp_tool(tool_name: str, arguments: dict) -> dict:
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, call_mcp_tool(tool_name, arguments)).result()

        return asyncio.run(call_mcp_tool(tool_name, arguments))
    except Exception as exc:
        logger.error("invoke_mcp_tool(%s) → ERRO: %s", tool_name, exc, exc_info=True)
        return {"success": False, "message": f"Erro de comunicação com o servidor MCP: {exc}"}
