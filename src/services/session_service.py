class SessionService:
    def end_conversation(self, reason: str = "") -> dict:
        return {
            "ended": True,
            "reason": reason.strip() or "Encerramento solicitado pelo cliente.",
            "message": "Atendimento encerrado.",
        }
