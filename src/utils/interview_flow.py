import re
from typing import Any, Optional

INTERVIEW_FIELD_ORDER = [
    "monthly_income",
    "job_type",
    "monthly_expenses",
    "dependents",
    "has_debts",
]

INTERVIEW_FIELD_LABELS = {
    "monthly_income": "renda mensal",
    "job_type": "tipo de emprego",
    "monthly_expenses": "despesas fixas mensais",
    "dependents": "número de dependentes",
    "has_debts": "dívidas ativas",
}

INTERVIEW_QUESTIONS = {
    "monthly_income": "Para começarmos, qual é a sua **renda mensal** bruta (em reais)?",
    "job_type": "Qual é o seu **tipo de emprego**? Responda: formal, autônomo ou desempregado.",
    "monthly_expenses": "Quais são suas **despesas fixas mensais** (em reais)?",
    "dependents": "Quantos **dependentes** você possui?",
    "has_debts": "Você possui **dívidas ativas** no momento? Responda sim ou não.",
}

INTERVIEW_OPENING = (
    "Perfeito, {first_name}! Vamos iniciar sua **entrevista de crédito**.\n"
    "Vou fazer algumas perguntas financeiras, uma de cada vez.\n\n"
    + INTERVIEW_QUESTIONS["monthly_income"]
)


def interview_fields_complete(collected: Optional[dict]) -> bool:
    if not collected:
        return False
    return all(field in collected for field in INTERVIEW_FIELD_ORDER)


def next_interview_field(collected: Optional[dict]) -> Optional[str]:
    collected = collected or {}
    for field in INTERVIEW_FIELD_ORDER:
        if field not in collected:
            return field
    return None


def _parse_money(value: str) -> Optional[float]:
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("r$", "").replace(" ", "")
    cleaned = cleaned.replace(".", "").replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    try:
        amount = float(match.group(1))
    except ValueError:
        return None
    return amount if amount >= 0 else None


def _parse_job_type(value: str) -> Optional[str]:
    text = value.strip().lower()
    if "formal" in text or "clt" in text or "carteira" in text:
        return "formal"
    if "aut" in text or "freela" in text or "mei" in text:
        return "autônomo"
    if "desempreg" in text or "sem emprego" in text or "desocupad" in text:
        return "desempregado"
    return None


def _parse_dependents(value: str) -> Optional[int]:
    match = re.search(r"\d+", value.strip())
    if not match:
        return None
    try:
        count = int(match.group(0))
    except ValueError:
        return None
    return count if count >= 0 else None


def _parse_has_debts(value: str) -> Optional[bool]:
    text = value.strip().lower()
    yes_words = ("sim", "tenho", "possuo", "s", "yes")
    no_words = ("não", "nao", "n", "negativo", "sem divida", "sem dívida", "no")
    if any(word in text for word in yes_words) and not any(
        word in text for word in ("não", "nao", "sem")
    ):
        return True
    if any(word in text for word in no_words):
        return False
    return None


def parse_interview_field(field: str, value: str) -> tuple[Optional[Any], Optional[str]]:
    if field == "monthly_income":
        parsed = _parse_money(value)
        if parsed is None:
            return None, "Informe a renda mensal em reais (ex.: 5000 ou R$ 5.000,00)."
        return parsed, None

    if field == "job_type":
        parsed = _parse_job_type(value)
        if parsed is None:
            return None, "Informe o tipo de emprego: formal, autônomo ou desempregado."
        return parsed, None

    if field == "monthly_expenses":
        parsed = _parse_money(value)
        if parsed is None:
            return None, "Informe as despesas fixas mensais em reais."
        return parsed, None

    if field == "dependents":
        parsed = _parse_dependents(value)
        if parsed is None:
            return None, "Informe o número de dependentes (ex.: 0, 1, 2)."
        return parsed, None

    if field == "has_debts":
        parsed = _parse_has_debts(value)
        if parsed is None:
            return None, "Responda sim ou não sobre dívidas ativas."
        return parsed, None

    return None, "Campo de entrevista inválido."
