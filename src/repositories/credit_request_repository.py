import csv
import os
from src.models import CreditIncreaseRequest


class CreditRequestRepository:
    def __init__(self, filepath: str = "data/solicitacoes_aumento_limite.csv"):
        self.filepath = filepath
        self._init_csv()

    def _init_csv(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["cpf_cliente", "data_hora_solicitacao", "limite_atual", "novo_limite_solicitado", "status_pedido"])

    def save(self, request: CreditIncreaseRequest) -> None:
        row = request.model_dump(by_alias=True)
        row["data_hora_solicitacao"] = request.request_datetime.isoformat()

        with open(self.filepath, "a", newline="", encoding="utf-8") as f:
            fieldnames = ["cpf_cliente", "data_hora_solicitacao", "limite_atual", "novo_limite_solicitado", "status_pedido"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if os.path.getsize(self.filepath) == 0:
                writer.writeheader()

            writer.writerow(row)
