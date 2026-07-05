from unittest.mock import Mock, patch

import pytest
import requests

from src.services.exchange_service import ExchangeService


MOCK_USD_RESPONSE = {
    "USDBRL": {
        "code": "USD",
        "codein": "BRL",
        "name": "Dólar Americano/Real Brasileiro",
        "high": "5.20",
        "low": "5.10",
        "pctChange": "0.35",
        "bid": "5.1523",
        "ask": "5.1545",
        "create_date": "2026-07-05 10:00:00",
    }
}


@pytest.fixture
def exchange_service():
    return ExchangeService()


@pytest.mark.parametrize(
    "input_currency,expected",
    [
        ("USD", "USD"),
        ("dólar", "USD"),
        ("dolar", "USD"),
        ("euro", "EUR"),
        ("EUR", "EUR"),
        ("libra", "GBP"),
        ("", "USD"),
    ],
)
def test_normalize_currency(exchange_service, input_currency, expected):
    assert exchange_service.normalize_currency(input_currency) == expected


def test_normalize_currency_unknown(exchange_service):
    assert exchange_service.normalize_currency("bitcoin") is None


@patch("src.services.exchange_service.requests.get")
def test_get_quote_success(mock_get, exchange_service):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = MOCK_USD_RESPONSE
    mock_get.return_value = mock_response

    success, data, message = exchange_service.get_quote("dólar")

    assert success is True
    assert data["currency_code"] == "USD"
    assert data["pair"] == "USD-BRL"
    assert data["bid"] == pytest.approx(5.1523)
    assert data["ask"] == pytest.approx(5.1545)
    assert message == "Cotação consultada com sucesso."
    mock_get.assert_called_once_with(
        "https://economia.awesomeapi.com.br/last/USD-BRL",
        timeout=10.0,
    )


@patch("src.services.exchange_service.requests.get")
def test_get_quote_api_failure(mock_get, exchange_service):
    mock_get.side_effect = requests.ConnectionError("offline")

    success, data, message = exchange_service.get_quote("USD")

    assert success is False
    assert data == {}
    assert "não foi possível consultar" in message.lower()


@patch("src.services.exchange_service.requests.get")
def test_get_quote_timeout(mock_get, exchange_service):
    mock_get.side_effect = requests.Timeout()

    success, data, message = exchange_service.get_quote("EUR")

    assert success is False
    assert data == {}
    assert "demorou demais" in message.lower()


@patch("src.services.exchange_service.requests.get")
def test_get_quote_invalid_response(mock_get, exchange_service):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"USDBRL": {"bid": "invalid"}}
    mock_get.return_value = mock_response

    success, data, message = exchange_service.get_quote("USD")

    assert success is False
    assert data == {}
    assert "inválida" in message.lower()


def test_get_quote_unsupported_currency(exchange_service):
    success, data, message = exchange_service.get_quote("bitcoin")

    assert success is False
    assert data == {}
    assert "não reconhecida" in message.lower()
