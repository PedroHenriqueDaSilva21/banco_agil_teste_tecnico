from langchain_core.messages import ToolMessage

from src.agents.exchange import _apply_tool_side_effects


def test_end_conversation_sets_flag():
    state = {
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


def test_get_currency_quote_sets_quote_delivered_flag():
    state = {
        "conversation_ended": False,
        "quote_delivered": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"success": true, "currency_code": "USD", "bid": 5.15}',
            tool_call_id="1",
            name="get_currency_quote",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["conversation_ended"] is False
    assert result["quote_delivered"] is True


def test_get_currency_quote_does_not_end_conversation():
    state = {
        "conversation_ended": False,
        "quote_delivered": False,
    }
    tool_messages = [
        ToolMessage(
            content='{"success": true, "currency_code": "USD", "bid": 5.15}',
            tool_call_id="1",
            name="get_currency_quote",
        )
    ]

    result = _apply_tool_side_effects(state, tool_messages)

    assert result["conversation_ended"] is False
