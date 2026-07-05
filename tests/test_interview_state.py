from langchain_core.messages import ToolMessage

from src.agents.interview import _apply_tool_side_effects


def test_submit_interview_updates_score():
    state = {
        "customer_score": 250.0,
        "target_agent": "interview",
        "returned_from_interview": False,
        "last_request_status": "rejeitado",
        "interview_offered": True,
        "conversation_ended": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"success": true, "previous_score": 250, "new_score": 555.0}',
            tool_call_id="1",
            name="submit_credit_interview",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["customer_score"] == 555.0
    assert result["returned_from_interview"] is False


def test_redirect_to_credit_sets_target_and_flags():
    state = {
        "customer_score": 555.0,
        "target_agent": "interview",
        "returned_from_interview": False,
        "last_request_status": "rejeitado",
        "interview_offered": True,
        "conversation_ended": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"redirected": true, "target_agent": "credit"}',
            tool_call_id="1",
            name="redirect_to_credit",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["target_agent"] == "credit"
    assert result["returned_from_interview"] is True
    assert result["last_request_status"] is None
    assert result["interview_offered"] is False


def test_end_conversation_sets_flag():
    state = {
        "target_agent": "interview",
        "conversation_ended": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"ended": true}',
            tool_call_id="1",
            name="end_conversation",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["conversation_ended"] is True
