import csv
import os


class ScoreLimitRepository:
    def __init__(self, filepath: str = "data/score_limite.csv"):
        self.filepath = filepath
        self._init_csv()

    def _init_csv(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["score_minimo", "limite_maximo"])

    def get_max_limit_by_score(self, score: float) -> float:
        max_limit = 0.0
        with open(self.filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    score_min = float(row.get("score_minimo", 0))
                    limite_max = float(row.get("limite_maximo", 0))
                    if score >= score_min:
                        if limite_max > max_limit:
                            max_limit = limite_max
                except (ValueError, TypeError):
                    continue
        return max_limit
