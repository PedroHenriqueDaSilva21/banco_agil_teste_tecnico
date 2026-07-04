import csv
import os
from typing import Optional
from src.models import Customer


class CustomerRepository:
    def __init__(self, filepath: str = "data/clientes.csv"):
        self.filepath = filepath
        self._init_csv()

    def _init_csv(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["cpf", "nome", "data_nascimento", "score", "limite_atual"])

    def get_by_cpf(self, cpf: str) -> Optional[Customer]:
        clean_cpf = "".join(char for char in cpf if char.isdigit())
        if not clean_cpf:
            return None

        with open(self.filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_cpf = "".join(char for char in row.get("cpf", "") if char.isdigit())
                if row_cpf == clean_cpf:
                    return Customer(**row)
        return None

    def update_score_and_limit(self, cpf: str, new_score: float, new_limit: float) -> bool:
        clean_cpf = "".join(char for char in cpf if char.isdigit())
        if not clean_cpf:
            return False

        rows = []
        updated = False

        with open(self.filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                row_cpf = "".join(char for char in row.get("cpf", "") if char.isdigit())
                if row_cpf == clean_cpf:
                    row["score"] = str(new_score)
                    row["limite_atual"] = str(new_limit)
                    updated = True
                rows.append(row)

        if updated:
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        return updated
