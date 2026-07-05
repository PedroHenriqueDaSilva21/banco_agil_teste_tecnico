import re
from typing import Optional


# Padrões conhecidos de tentativas de prompt injection
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"forget\s+(all\s+)?(previous|above|prior|your)\s+instructions?",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a|an|if)",
    r"new\s+instructions?:",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"\[system\]",
    r"do\s+not\s+follow\s+your\s+(instructions?|rules?|guidelines?)",
    r"override\s+(your\s+)?(instructions?|rules?|behavior)",
    r"jailbreak",
    r"pretend\s+(you\s+are|to\s+be)",
    r"roleplay\s+as",
    r"your\s+(true|real|actual)\s+(self|identity|purpose)",
    r"disregard\s+(all\s+)?(previous|your)\s+(instructions?|rules?)",
]

_COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in _INJECTION_PATTERNS
]

# Tamanho máximo de uma mensagem de usuário (proteção contra ataques por volume)
MAX_INPUT_LENGTH = 1000


def sanitize_input(text: str) -> Optional[str]:
    """
    Sanitiza a entrada do usuário para prevenir prompt injection.

    Aplica as seguintes verificações:
    - Limite de comprimento da mensagem.
    - Detecção de padrões conhecidos de tentativas de injeção.

    Args:
        text: O texto de entrada do usuário.

    Returns:
        O texto sanitizado se for considerado seguro, ou None se for bloqueado.
    """
    if not text or not text.strip():
        return None

    if len(text) > MAX_INPUT_LENGTH:
        return None

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return None

    return text.strip()


def is_safe_input(text: str) -> bool:
    """
    Verifica se a entrada é segura sem retornar o texto.

    Returns:
        True se a entrada for segura, False se for suspeita.
    """
    return sanitize_input(text) is not None
