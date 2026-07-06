from langchain_core.messages import ToolMessage

from src.agents.triage import _apply_tool_side_effects


def test_auth_failure_increments_attempts():
    state = {"auth_attempts": 0, "authenticated": False, "conversation_ended": False}
    tool_messages = [
        ToolMessage(
            content='{"success": false, "message": "Cliente não encontrado."}',
            tool_call_id="1",
            name="authenticate_customer",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["auth_attempts"] == 1
    assert result["authenticated"] is False
    assert result["conversation_ended"] is False


def test_auth_lockout_after_three_failures():
    state = {"auth_attempts": 2, "authenticated": False, "conversation_ended": False}
    tool_messages = [
        ToolMessage(
            content='{"success": false, "message": "Data de nascimento incorreta."}',
            tool_call_id="1",
            name="authenticate_customer",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["auth_attempts"] == 3
    assert result["conversation_ended"] is True
    assert len(result["extra_messages"]) == 1


def test_auth_success_sets_customer_fields():
    state = {"auth_attempts": 0, "authenticated": False, "conversation_ended": False, "auth_menu_delivered": False}
    tool_messages = [
        ToolMessage(
            content=(
                '{"success": true, "customer_name": "Ana Silva", '
                '"customer_cpf": "12345678901", "customer_score": 629.85, '
                '"customer_limit": 2500.0}'
            ),
            tool_call_id="1",
            name="authenticate_customer",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["authenticated"] is True
    assert result["customer_name"] == "Ana Silva"
    assert result["customer_cpf"] == "12345678901"
    assert result["customer_score"] == 629.85
    assert result["customer_limit"] == 2500.0
    assert result["auth_menu_delivered"] is True
    assert len(result["extra_messages"]) == 1
    assert "1. **Crédito**" in result["extra_messages"][0].content
    assert "2. **Entrevista de crédito**" in result["extra_messages"][0].content
    assert "3. **Câmbio**" in result["extra_messages"][0].content


def test_classify_intent_sets_target_agent():
    state = {"target_agent": None, "intent": None, "conversation_ended": False}
    tool_messages = [
        ToolMessage(
            content='{"intent": "EXCHANGE", "target_agent": "exchange", "message": "ok"}',
            tool_call_id="1",
            name="classify_intent",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["target_agent"] == "exchange"
    assert result["intent"] == "EXCHANGE"


def test_end_conversation_sets_flag():
    state = {"conversation_ended": False}
    tool_messages = [
        ToolMessage(
            content='{"ended": true, "message": "Atendimento encerrado."}',
            tool_call_id="1",
            name="end_conversation",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["conversation_ended"] is True
