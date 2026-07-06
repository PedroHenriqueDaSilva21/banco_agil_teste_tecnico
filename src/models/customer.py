from pydantic import BaseModel, Field, field_validator


class Customer(BaseModel):
    cpf: str = Field(..., description="Customer CPF with 11 digits")
    name: str = Field(..., validation_alias="nome", serialization_alias="nome", min_length=1, description="Customer full name")
    birth_date: str = Field(..., validation_alias="data_nascimento", serialization_alias="data_nascimento", description="Customer birth date")
    score: float = Field(ge=0, le=1000, description="Customer credit score")
    current_limit: float = Field(default=0, ge=0, validation_alias="limite_atual", serialization_alias="limite_atual", description="Current available limit")

    model_config = {
        "populate_by_name": True
    }

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) != 11:
            raise ValueError("CPF must contain 11 digits")
        return digits