import pytest

from src.services.routing import IntentTag, RoutingService


@pytest.fixture
def routing_service():
    return RoutingService()


@pytest.mark.parametrize(
    "message,expected_intent,expected_agent",
    [
        ("Qual é o meu limite de crédito?", IntentTag.CREDIT_LIMIT, "credit"),
        ("Quero consultar meu limite", IntentTag.CREDIT_LIMIT, "credit"),
        ("Preciso aumentar meu limite de crédito", IntentTag.CREDIT_INCREASE, "credit"),
        ("Quero solicitar aumento", IntentTag.CREDIT_INCREASE, "credit"),
        ("Quero fazer a entrevista de crédito", IntentTag.CREDIT_INTERVIEW, "interview"),
        ("Preciso reavaliar meu score", IntentTag.CREDIT_INTERVIEW, "interview"),
        ("2", IntentTag.CREDIT_INTERVIEW, "interview"),
        ("Qual a cotação do dólar?", IntentTag.EXCHANGE, "exchange"),
        ("Preciso de câmbio", IntentTag.EXCHANGE, "exchange"),
        ("Quanto está o euro hoje?", IntentTag.EXCHANGE, "exchange"),
        ("3", IntentTag.EXCHANGE, "exchange"),
        ("1", IntentTag.CREDIT_LIMIT, "credit"),
    ],
)
def test_classify_known_intents(routing_service, message, expected_intent, expected_agent):
    result = routing_service.classify_intent(message)
    assert result["intent"] == expected_intent.value
    assert result["target_agent"] == expected_agent


def test_classify_unknown_intent(routing_service):
    result = routing_service.classify_intent("Preciso de ajuda com outra coisa")
    assert result["intent"] == IntentTag.UNKNOWN.value
    assert result["target_agent"] is None


def test_classify_empty_message(routing_service):
    result = routing_service.classify_intent("   ")
    assert result["intent"] == IntentTag.UNKNOWN.value
