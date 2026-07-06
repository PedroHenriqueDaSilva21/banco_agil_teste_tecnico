import re
from enum import Enum
from typing import Optional


class IntentTag(str, Enum):
    CREDIT_LIMIT = "CREDIT_LIMIT"
    CREDIT_INCREASE = "CREDIT_INCREASE"
    CREDIT_INTERVIEW = "CREDIT_INTERVIEW"
    EXCHANGE = "EXCHANGE"
    UNKNOWN = "UNKNOWN"


AGENT_BY_INTENT: dict[IntentTag, Optional[str]] = {
    IntentTag.CREDIT_LIMIT: "credit",
    IntentTag.CREDIT_INCREASE: "credit",
    IntentTag.CREDIT_INTERVIEW: "interview",
    IntentTag.EXCHANGE: "exchange",
    IntentTag.UNKNOWN: None,
}


_MENU_OPTION_PATTERNS: list[tuple[str, IntentTag]] = [
    (r"^\s*1\s*$", IntentTag.CREDIT_LIMIT),
    (r"^\s*2\s*$", IntentTag.CREDIT_INTERVIEW),
    (r"^\s*3\s*$", IntentTag.EXCHANGE),
    (r"\bop[cç][aã]o\s*1\b", IntentTag.CREDIT_LIMIT),
    (r"\bop[cç][aã]o\s*2\b", IntentTag.CREDIT_INTERVIEW),
    (r"\bop[cç][aã]o\s*3\b", IntentTag.EXCHANGE),
]

_CREDIT_INTERVIEW_PATTERNS = [
    r"\bentrevista\b",
    r"\breavali(ar|ação)\b.*\bscore\b",
    r"\batualizar\b.*\bscore\b",
    r"\bscore\b.*\b(cr[eé]dito|financeir[oa])\b",
]


_CREDIT_LIMIT_PATTERNS = [
    r"\blimite\b",
    r"\bcr[eé]dito\s+dispon[ií]vel\b",
    r"\bquanto\s+(tenho|posso|disponho)\b",
    r"\bmeu\s+limite\b",
    r"\bconsultar\s+(limite|cr[eé]dito)\b",
]

_CREDIT_INCREASE_PATTERNS = [
    r"\baument(o|ar)\b.*\blimite\b",
    r"\baument(o|ar)\b.*\bcr[eé]dito\b",
    r"\bmais\s+cr[eé]dito\b",
    r"\bexpandir\s+limite\b",
    r"\bsolicitar\s+aumento\b",
]

_EXCHANGE_PATTERNS = [
    r"\bc[aâ]mbio\b",
    r"\bcota[cç][aã]o\b",
    r"\bd[oó]lar\b",
    r"\beuro\b",
    r"\bmoeda\b",
    r"\busd\b",
    r"\breal\s+x\s+d[oó]lar\b",
]


class RoutingService:
    def classify_intent(self, user_message: str) -> dict:
        text = user_message.strip().lower()
        if not text:
            return self._result(IntentTag.UNKNOWN, "Mensagem vazia.")

        for pattern, intent in _MENU_OPTION_PATTERNS:
            if re.search(pattern, text):
                return self._result(intent, f"Opção de menu identificada: {intent.value}.")

        if self._matches_any(text, _EXCHANGE_PATTERNS):
            return self._result(IntentTag.EXCHANGE, "Intenção de consulta de câmbio identificada.")

        if self._matches_any(text, _CREDIT_INTERVIEW_PATTERNS):
            return self._result(
                IntentTag.CREDIT_INTERVIEW,
                "Intenção de entrevista de crédito identificada.",
            )

        if self._matches_any(text, _CREDIT_INCREASE_PATTERNS):
            return self._result(IntentTag.CREDIT_INCREASE, "Intenção de aumento de limite identificada.")

        if self._matches_any(text, _CREDIT_LIMIT_PATTERNS):
            return self._result(IntentTag.CREDIT_LIMIT, "Intenção de consulta de limite identificada.")

        if self._matches_any(text, [r"\bcr[eé]dito\b"]):
            return self._result(IntentTag.CREDIT_LIMIT, "Intenção relacionada a crédito identificada.")

        return self._result(IntentTag.UNKNOWN, "Não foi possível identificar a intenção com clareza.")

    def _matches_any(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)

    def _result(self, intent: IntentTag, message: str) -> dict:
        target_agent = AGENT_BY_INTENT[intent]
        return {
            "intent": intent.value,
            "target_agent": target_agent,
            "message": message,
        }
