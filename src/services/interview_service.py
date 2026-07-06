from typing import Optional, Tuple

from src.models import CreditInterview, CreditScoreResult
from src.repositories import CustomerRepository

PESO_RENDA = 30

PESO_EMPREGO = {
    "formal": 300,
    "autônomo": 200,
    "desempregado": 0,
}

PESO_DEPENDENTES = {
    0: 100,
    1: 80,
    2: 60,
}

PESO_DIVIDAS = {
    True: -100,
    False: 100,
}


class InterviewService:
    def __init__(self, customer_repo: Optional[CustomerRepository] = None):
        self.customer_repo = customer_repo or CustomerRepository()

    def _dependents_weight(self, dependents: int) -> float:
        if dependents >= 3:
            return 30
        return PESO_DEPENDENTES.get(dependents, 30)

    def calculate_score(self, interview: CreditInterview) -> CreditScoreResult:
        income_component = (interview.monthly_income / (interview.monthly_expenses + 1)) * PESO_RENDA
        employment_component = PESO_EMPREGO[interview.job_type]
        dependents_component = self._dependents_weight(interview.dependents)
        debts_component = PESO_DIVIDAS[interview.has_debts]

        raw_score = income_component + employment_component + dependents_component + debts_component
        new_score = min(1000.0, max(0.0, raw_score))

        justification = (
            f"Renda: ({interview.monthly_income:.2f} / {interview.monthly_expenses + 1:.2f}) × {PESO_RENDA} = {income_component:.2f}; "
            f"Emprego ({interview.job_type}): {employment_component}; "
            f"Dependentes ({interview.dependents}): {dependents_component}; "
            f"Dívidas ({'sim' if interview.has_debts else 'não'}): {debts_component}."
        )

        return CreditScoreResult(
            previous_score=0,
            new_score=new_score,
            justification=justification,
        )

    def submit_interview(self, cpf: str, interview: CreditInterview) -> Tuple[bool, dict, str]:
        customer = self.customer_repo.get_by_cpf(cpf)
        if not customer:
            return False, {}, "Cliente não encontrado."

        result = self.calculate_score(interview)
        result.previous_score = customer.score

        updated = self.customer_repo.update_score_and_limit(
            cpf,
            result.new_score,
            customer.current_limit,
        )
        if not updated:
            return False, {}, "Não foi possível atualizar o score do cliente."

        return True, {
            "previous_score": result.previous_score,
            "new_score": result.new_score,
            "justification": result.justification,
        }, "Entrevista registrada e score atualizado com sucesso."
