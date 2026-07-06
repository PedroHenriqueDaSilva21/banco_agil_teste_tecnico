from datetime import datetime

from pydantic import BaseModel, Field


class CreditIncreaseRequest(BaseModel):
    customer_cpf: str = Field(..., validation_alias="cpf_cliente", serialization_alias="cpf_cliente", description="CPF of the customer")
    request_datetime: datetime = Field(..., validation_alias="data_hora_solicitacao", serialization_alias="data_hora_solicitacao")
    current_limit: float = Field(ge=0, validation_alias="limite_atual", serialization_alias="limite_atual", description="Current credit limit")
    requested_limit: float = Field(ge=0, validation_alias="novo_limite_solicitado", serialization_alias="novo_limite_solicitado", description="Requested credit limit")
    request_status: str = Field(..., validation_alias="status_pedido", serialization_alias="status_pedido", description="Request status")

    model_config = {
        "populate_by_name": True
    }