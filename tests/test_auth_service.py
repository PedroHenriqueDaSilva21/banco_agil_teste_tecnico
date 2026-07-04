import csv
import os
import pytest
from src.repositories import CustomerRepository
from src.services import AuthService


@pytest.fixture
def temp_clientes_csv(tmp_path):
    csv_file = tmp_path / "clientes.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cpf", "nome", "data_nascimento", "score", "limite_atual"])
        writer.writerow(["12345678901", "Ana Silva", "1990-01-15", "600", "1500"])
        writer.writerow(["98765432100", "Bruno Santos", "1985-11-20", "250", "500"])
    return str(csv_file)


@pytest.fixture
def auth_service(temp_clientes_csv):
    repo = CustomerRepository(filepath=temp_clientes_csv)
    return AuthService(customer_repo=repo)


def test_authenticate_success(auth_service):
    success, customer, message = auth_service.authenticate("12345678901", "1990-01-15")
    assert success is True
    assert customer is not None
    assert customer.name == "Ana Silva"
    assert message == "Autenticação realizada com sucesso."


def test_authenticate_success_with_formatting(auth_service):
    # Teste de robustez com CPF formatado e data em outro padrão (DD/MM/YYYY)
    success, customer, message = auth_service.authenticate("123.456.789-01", "15/01/1990")
    assert success is True
    assert customer is not None
    assert customer.name == "Ana Silva"


def test_authenticate_customer_not_found(auth_service):
    success, customer, message = auth_service.authenticate("00000000000", "1990-01-15")
    assert success is False
    assert customer is None
    assert message == "Cliente não encontrado."


def test_authenticate_wrong_birthdate(auth_service):
    success, customer, message = auth_service.authenticate("12345678901", "1990-01-20")
    assert success is False
    assert customer is None
    assert message == "Data de nascimento incorreta."
