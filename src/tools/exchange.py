import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.mcp_client import invoke_mcp_tool
from src.utils import load_prompt

logger = logging.getLogger(__name__)


class GetCurrencyQuoteSchema(BaseModel):
    currency: str = Field(
        default="USD",
        description=(
            "Código ou nome da moeda desejada (ex.: USD, dólar, EUR, euro, GBP, libra). "
            "Padrão: USD (dólar americano)."
        ),
    )


@tool(
    description=load_prompt("tools/get_currency_quote_tool_description.txt"),
    args_schema=GetCurrencyQuoteSchema,
)
def get_currency_quote(currency: str = "USD") -> dict:
    logger.info("get_currency_quote chamada — currency=%s", currency)
    result = invoke_mcp_tool("get_currency_quote", {"currency": currency})
    logger.info(
        "get_currency_quote → success=%s pair=%s",
        result.get("success"),
        result.get("pair"),
    )
    return result
