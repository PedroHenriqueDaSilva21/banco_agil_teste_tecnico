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
        "interview_collected": {},
        "interview_submitted": False,
        "interview_await_user": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"success": true, "field": "monthly_income", "value": 8000.0}',
            tool_call_id="1",
            name="record_interview_answer",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["interview_collected"]["monthly_income"] == 8000.0
    assert result["interview_await_user"] is True
    assert len(result["extra_messages"]) == 1


def test_record_last_field_triggers_submit(monkeypatch):
    from src.agents import interview as interview_module

    state = {
        "customer_cpf": "12345678901",
        "customer_score": 250.0,
        "target_agent": "interview",
        "returned_from_interview": False,
        "last_request_status": "rejeitado",
        "interview_offered": True,
        "conversation_ended": False,
        "interview_collected": {
            "monthly_income": 8000.0,
            "job_type": "formal",
            "monthly_expenses": 1500.0,
            "dependents": 0,
        },
        "interview_submitted": False,
        "interview_await_user": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"success": true, "field": "has_debts", "value": false}',
            tool_call_id="1",
            name="record_interview_answer",
        )
    ]

    monkeypatch.setattr(
        interview_module,
        "submit_collected_interview",
        lambda cpf, collected: {
            "success": True,
            "previous_score": 250.0,
            "new_score": 555.0,
            "message": "Entrevista registrada.",
        },
    )

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["customer_score"] == 555.0
    assert result["interview_submitted"] is True
    assert result["target_agent"] == "credit"
    assert result["returned_from_interview"] is True


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
