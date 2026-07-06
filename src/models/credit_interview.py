from typing import Literal

from pydantic import BaseModel, Field


class CreditInterview(BaseModel):
    monthly_income: float = Field(ge=0, description="Monthly income")
    job_type: Literal["formal", "autônomo", "desempregado"] = Field(..., description="Job type")
    monthly_expenses: float = Field(ge=0, description="Monthly fixed expenses")
    dependents: int = Field(ge=0, description="Number of dependents")
    has_debts: bool = Field(..., description="Whether the customer has active debts")