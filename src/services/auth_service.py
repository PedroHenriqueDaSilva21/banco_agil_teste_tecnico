from datetime import datetime
from typing import Optional, Tuple
from src.models import Customer
from src.repositories import CustomerRepository


class AuthService:
    def __init__(self, customer_repo: Optional[CustomerRepository] = None):
        self.customer_repo = customer_repo or CustomerRepository()

    def _normalize_date(self, date_str: str) -> Optional[str]:
        date_str = date_str.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        digits = "".join(char for char in date_str if char.isdigit())
        if len(digits) == 8:
            for fmt in ("%d%m%Y", "%Y%m%d"):
                try:
                    return datetime.strptime(digits, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None

    def authenticate(self, cpf: str, birth_date: str) -> Tuple[bool, Optional[Customer], str]:
        customer = self.customer_repo.get_by_cpf(cpf)
        if not customer:
            return False, None, "Cliente não encontrado."

        normalized_input = self._normalize_date(birth_date)
        normalized_db = self._normalize_date(customer.birth_date)

        if not normalized_input or normalized_input != normalized_db:
            return False, None, "Data de nascimento incorreta."

        return True, customer, "Autenticação realizada com sucesso."

