
import asyncio
import json
import logging
import os
import sys

from langchain_core.tools import tool

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.utils import mask_cpf, mask_date

logger = logging.getLogger(__name__)


@tool
def authenticate_customer(cpf: str, birth_date: str) -> dict:
    """
    Autentica o cliente no sistema do Banco Ágil usando CPF e data de nascimento.
    Deve ser chamada assim que o cliente fornecer o CPF e a data de nascimento.

    Args:
        cpf: O CPF do cliente (apenas números ou formatado com pontos e traço).
        birth_date: A data de nascimento do cliente (aceita DD/MM/YYYY ou YYYY-MM-DD).

    Returns:
        Um dicionário com:
        - success (bool): Se a autenticação foi bem-sucedida.
        - message (str): Mensagem explicativa do resultado.
        - customer_name (str, opcional): Nome do cliente autenticado.
    """
    logger.info(
        "authenticate_customer chamada — cpf=%s nascimento=%s",
        mask_cpf(cpf),
        mask_date(birth_date),
    )

    async def _call_mcp() -> dict:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            env=dict(os.environ),
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool(
                    "authenticate_customer",
                    {"cpf": cpf, "birth_date": birth_date},
                )

                if not response.content:
                    return {"success": False, "message": "Sem resposta do servidor MCP."}

                raw = response.content[0].text
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    try:
                        import ast
                        return ast.literal_eval(raw)
                    except Exception:
                        return {"success": False, "message": f"Resposta inesperada do MCP: {raw}"}

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        result = (
            asyncio.get_event_loop().run_until_complete(_call_mcp())
            if loop and loop.is_running()
            else asyncio.run(_call_mcp())
        )

        status = "OK" if result.get("success") else "FAIL"
        logger.info(
            "authenticate_customer → %s: %s",
            status,
            result.get("message", ""),
        )
        return result

    except Exception as exc:
        logger.error("authenticate_customer → ERRO: %s", exc, exc_info=True)
        return {"success": False, "message": f"Erro de comunicação com o servidor MCP: {exc}"}
