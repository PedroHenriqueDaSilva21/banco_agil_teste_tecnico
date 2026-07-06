from datetime import datetime, timezone
from typing import Optional, Tuple

from src.models import CreditIncreaseRequest
from src.repositories import CreditRequestRepository, CustomerRepository, ScoreLimitRepository


class CreditService:
    def __init__(
        self,
        customer_repo: Optional[CustomerRepository] = None,
        credit_request_repo: Optional[CreditRequestRepository] = None,
        score_limit_repo: Optional[ScoreLimitRepository] = None,
    ):
        self.customer_repo = customer_repo or CustomerRepository()
        self.credit_request_repo = credit_request_repo or CreditRequestRepository()
        self.score_limit_repo = score_limit_repo or ScoreLimitRepository()

    def get_credit_limit(self, cpf: str) -> Tuple[bool, dict, str]:
        customer = self.customer_repo.get_by_cpf(cpf)
        if not customer:
            return False, {}, "Cliente não encontrado."

        max_allowed = self.score_limit_repo.get_max_limit_by_score(customer.score)
        return True, {
            "customer_name": customer.name,
            "current_limit": customer.current_limit,
            "score": customer.score,
            "max_allowed_limit": max_allowed,
        }, "Limite consultado com sucesso."

    def request_limit_increase(self, cpf: str, requested_limit: float) -> Tuple[bool, dict, str]:
        customer = self.customer_repo.get_by_cpf(cpf)
        if not customer:
            return False, {}, "Cliente não encontrado."

        if requested_limit <= 0:
            return False, {}, "O limite solicitado deve ser maior que zero."

        if requested_limit <= customer.current_limit:
            return False, {}, "O novo limite deve ser maior que o limite atual."

        max_allowed = self.score_limit_repo.get_max_limit_by_score(customer.score)
        status = "aprovado" if requested_limit <= max_allowed else "rejeitado"

        if status == "aprovado":
            self.customer_repo.update_score_and_limit(cpf, customer.score, requested_limit)
            message = "Solicitação aprovada com sucesso."
        else:
            message = "Solicitação rejeitada. Score insuficiente para o limite solicitado."

        request = CreditIncreaseRequest(
            customer_cpf=cpf,
            request_datetime=datetime.now(timezone.utc),
            current_limit=customer.current_limit,
            requested_limit=requested_limit,
            request_status=status,
        )
        self.credit_request_repo.save(request)

        return True, {
            "status": status,
            "current_limit": customer.current_limit,
            "requested_limit": requested_limit,
            "max_allowed_limit": max_allowed,
            "new_limit": requested_limit if status == "aprovado" else customer.current_limit,
        }, message
