import csv
import pytest

from src.repositories import CreditRequestRepository, CustomerRepository, ScoreLimitRepository
from src.services.credit_service import CreditService


@pytest.fixture
def credit_fixtures(tmp_path):
    clientes = tmp_path / "clientes.csv"
    score_limite = tmp_path / "score_limite.csv"
    solicitacoes = tmp_path / "solicitacoes.csv"

    with open(clientes, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cpf", "nome", "data_nascimento", "score", "limite_atual"])
        writer.writerow(["12345678901", "Ana Silva", "1990-01-15", "629", "2500"])

    with open(score_limite, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["score_minimo", "limite_maximo"])
        writer.writerow(["0", "0"])
        writer.writerow(["300", "1000"])
        writer.writerow(["500", "3000"])
        writer.writerow(["700", "5000"])

    service = CreditService(
        customer_repo=CustomerRepository(filepath=str(clientes)),
        credit_request_repo=CreditRequestRepository(filepath=str(solicitacoes)),
        score_limit_repo=ScoreLimitRepository(filepath=str(score_limite)),
    )
    return service, clientes, solicitacoes


def test_get_credit_limit_success(credit_fixtures):
    service, _, _ = credit_fixtures
    success, data, message = service.get_credit_limit("12345678901")

    assert success is True
    assert data["current_limit"] == 2500
    assert data["max_allowed_limit"] == 3000
    assert message == "Limite consultado com sucesso."


def test_request_increase_approved(credit_fixtures):
    service, clientes_path, solicitacoes_path = credit_fixtures
    success, data, message = service.request_limit_increase("12345678901", 3000)

    assert success is True
    assert data["status"] == "aprovado"
    assert data["new_limit"] == 3000
    assert "aprovada" in message.lower()

    customer = CustomerRepository(filepath=str(clientes_path)).get_by_cpf("12345678901")
    assert customer.current_limit == 3000

    with open(solicitacoes_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["status_pedido"] == "aprovado"


def test_request_increase_rejected(credit_fixtures):
    service, clientes_path, solicitacoes_path = credit_fixtures
    success, data, message = service.request_limit_increase("12345678901", 5000)

    assert success is True
    assert data["status"] == "rejeitado"
    assert "rejeitada" in message.lower()

    customer = CustomerRepository(filepath=str(clientes_path)).get_by_cpf("12345678901")
    assert customer.current_limit == 2500

    with open(solicitacoes_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["status_pedido"] == "rejeitado"


def test_request_increase_must_exceed_current(credit_fixtures):
    service, _, _ = credit_fixtures
    success, data, message = service.request_limit_increase("12345678901", 2000)

    assert success is False
    assert data == {}
    assert "maior que o limite atual" in message


def test_get_credit_limit_customer_not_found(credit_fixtures):
    service, _, _ = credit_fixtures
    success, data, message = service.get_credit_limit("00000000000")

    assert success is False
    assert data == {}
    assert message == "Cliente não encontrado."
