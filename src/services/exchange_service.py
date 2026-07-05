import logging
import re
import unicodedata
from typing import Optional, Tuple

import requests

from src.models import ExchangeQuote

logger = logging.getLogger(__name__)

AWESOME_API_BASE = "https://economia.awesomeapi.com.br/last"

CURRENCY_ALIASES: dict[str, str] = {
    "usd": "USD",
    "dolar": "USD",
    "dollar": "USD",
    "dolares": "USD",
    "dollars": "USD",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "gbp": "GBP",
    "libra": "GBP",
    "libra esterlina": "GBP",
    "ars": "ARS",
    "peso": "ARS",
    "peso argentino": "ARS",
    "cad": "CAD",
    "dolar canadense": "CAD",
    "jpy": "JPY",
    "iene": "JPY",
    "chf": "CHF",
    "franco": "CHF",
    "franco suico": "CHF",
}

SUPPORTED_CURRENCIES = sorted(set(CURRENCY_ALIASES.values()))


class ExchangeService:
    def __init__(self, api_base: str = AWESOME_API_BASE, timeout: float = 10.0):
        self.api_base = api_base
        self.timeout = timeout

    def _normalize_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.strip().lower())
        return "".join(char for char in normalized if not unicodedata.combining(char))

    def normalize_currency(self, currency: str) -> Optional[str]:
        if not currency or not currency.strip():
            return "USD"

        clean = self._normalize_text(currency)
        clean = re.sub(r"[^a-z0-9\s]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        if clean in CURRENCY_ALIASES:
            return CURRENCY_ALIASES[clean]

        upper = clean.upper()
        if upper in SUPPORTED_CURRENCIES:
            return upper

        for alias, code in CURRENCY_ALIASES.items():
            if alias in clean:
                return code

        return None

    def get_quote(self, currency: str = "USD") -> Tuple[bool, dict, str]:
        currency_code = self.normalize_currency(currency)
        if not currency_code:
            supported = ", ".join(SUPPORTED_CURRENCIES)
            return False, {}, f"Moeda não reconhecida. Moedas suportadas: {supported}."

        pair = f"{currency_code}-BRL"
        url = f"{self.api_base}/{pair}"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.Timeout:
            logger.error("Timeout ao consultar cotação — pair=%s", pair)
            return False, {}, "A consulta de cotação demorou demais. Tente novamente em instantes."
        except requests.RequestException as exc:
            logger.error("Falha na API de câmbio — pair=%s erro=%s", pair, exc)
            return False, {}, "Não foi possível consultar a cotação no momento. Tente novamente mais tarde."

        quote_key = f"{currency_code}BRL"
        raw = payload.get(quote_key)
        if not raw:
            return False, {}, f"Cotação indisponível para {currency_code}."

        try:
            quote = ExchangeQuote(
                currency_code=currency_code,
                currency_name=raw.get("name", pair),
                pair=pair,
                bid=float(raw["bid"]),
                ask=float(raw["ask"]),
                high=float(raw["high"]),
                low=float(raw["low"]),
                variation_pct=float(raw.get("pctChange", 0)),
                quoted_at=raw.get("create_date", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Resposta inválida da API de câmbio — pair=%s erro=%s", pair, exc)
            return False, {}, "Resposta inválida da API de câmbio. Tente novamente mais tarde."

        return True, quote.model_dump(), "Cotação consultada com sucesso."
