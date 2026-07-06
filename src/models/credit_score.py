from pydantic import BaseModel, Field


class CreditScoreResult(BaseModel):
    previous_score: float = Field(ge=0, le=1000, description="Previous credit score")
    new_score: float = Field(ge=0, le=1000, description="New credit score")
    justification: str = Field(default="", description="Score calculation justification")