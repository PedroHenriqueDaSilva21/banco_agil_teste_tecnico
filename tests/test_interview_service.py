import csv

import pytest

from src.models import CreditInterview
from src.repositories import CustomerRepository
from src.services.interview_service import InterviewService


@pytest.fixture
def interview_fixtures(tmp_path):
    clientes = tmp_path / "clientes.csv"

    with open(clientes, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cpf", "nome", "data_nascimento", "score", "limite_atual"])
        writer.writerow(["12345678901", "Ana Silva", "1990-01-15", "250", "2500"])

    service = InterviewService(customer_repo=CustomerRepository(filepath=str(clientes)))
    return service, clientes


def test_calculate_score_formula():
    service = InterviewService()
    interview = CreditInterview(
        monthly_income=6000,
        job_type="formal",
        monthly_expenses=2000,
        dependents=1,
        has_debts=False,
    )

    result = service.calculate_score(interview)

    income_component = (6000 / 2001) * 30
    expected = income_component + 300 + 80 + 100
    assert result.new_score == pytest.approx(min(1000.0, max(0.0, expected)), rel=1e-3)
    assert "Renda:" in result.justification


def test_calculate_score_clamped_to_max():
    service = InterviewService()
    interview = CreditInterview(
        monthly_income=50000,
        job_type="formal",
        monthly_expenses=100,
        dependents=0,
        has_debts=False,
    )

    result = service.calculate_score(interview)

    assert result.new_score == 1000.0


def test_calculate_score_unemployed_with_debts():
    service = InterviewService()
    interview = CreditInterview(
        monthly_income=0,
        job_type="desempregado",
        monthly_expenses=500,
        dependents=3,
        has_debts=True,
    )

    result = service.calculate_score(interview)

    assert result.new_score == 0.0


def test_submit_interview_updates_customer_score(interview_fixtures):
    service, clientes_path = interview_fixtures
    interview = CreditInterview(
        monthly_income=8000,
        job_type="formal",
        monthly_expenses=1500,
        dependents=0,
        has_debts=False,
    )

    success, data, message = service.submit_interview("12345678901", interview)

    assert success is True
    assert data["previous_score"] == 250
    assert data["new_score"] > 250
    assert "sucesso" in message.lower()

    customer = CustomerRepository(filepath=str(clientes_path)).get_by_cpf("12345678901")
    assert customer.score == data["new_score"]
    assert customer.current_limit == 2500


def test_submit_interview_customer_not_found(interview_fixtures):
    service, _ = interview_fixtures
    interview = CreditInterview(
        monthly_income=3000,
        job_type="autônomo",
        monthly_expenses=1000,
        dependents=1,
        has_debts=False,
    )

    success, data, message = service.submit_interview("00000000000", interview)

    assert success is False
    assert data == {}
    assert message == "Cliente não encontrado."
