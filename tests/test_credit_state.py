from langchain_core.messages import ToolMessage

from src.agents.credit import _apply_tool_side_effects


def test_request_increase_approved_updates_limit():
    state = {
        "customer_limit": 2500.0,
        "last_request_status": None,
        "interview_offered": False,
        "conversation_ended": False,
        "target_agent": "credit",
    }
    tool_messages = [
        ToolMessage(
            content=(
                '{"success": true, "status": "aprovado", "new_limit": 3000.0, '
                '"requested_limit": 3000.0}'
            ),
            tool_call_id="1",
            name="request_credit_increase",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["last_request_status"] == "aprovado"
    assert result["customer_limit"] == 3000.0
    assert result["interview_offered"] is False


def test_request_increase_rejected_offers_interview():
    state = {
        "customer_limit": 2500.0,
        "last_request_status": None,
        "interview_offered": False,
        "conversation_ended": False,
        "target_agent": "credit",
    }
    tool_messages = [
        ToolMessage(
            content='{"success": true, "status": "rejeitado", "new_limit": 2500.0}',
            tool_call_id="1",
            name="request_credit_increase",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["last_request_status"] == "rejeitado"
    assert result["interview_offered"] is True


def test_redirect_to_interview_changes_target():
    state = {
        "target_agent": "credit",
        "conversation_ended": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"redirected": true, "target_agent": "interview"}',
            tool_call_id="1",
            name="redirect_to_interview",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["target_agent"] == "interview"
