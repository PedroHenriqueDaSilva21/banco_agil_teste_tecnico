from src.services.session_service import SessionService


def test_end_conversation_default_reason():
    service = SessionService()
    result = service.end_conversation()

    assert result["ended"] is True
    assert result["message"] == "Atendimento encerrado."
    assert "Encerramento solicitado" in result["reason"]


def test_end_conversation_custom_reason():
    service = SessionService()
    result = service.end_conversation("Cliente pediu para sair.")

    assert result["ended"] is True
    assert result["reason"] == "Cliente pediu para sair."
