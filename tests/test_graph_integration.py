from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from tests.conftest import make_text_response, make_tool_call_response


@patch("src.agents.supervisor.create_triage_agent")
@patch("src.agents.supervisor.create_credit_agent")
@patch("src.agents.supervisor.create_interview_agent")
@patch("src.agents.supervisor.create_exchange_agent")
def test_supervisor_routes_to_credit(
    mock_exchange_factory,
    mock_interview_factory,
    mock_credit_factory,
    mock_triage_factory,
):
    from src.agents.state import initial_agent_state
    from src.agents.supervisor import create_supervisor

    mock_credit = MagicMock()
    mock_credit.invoke.return_value = {"messages": [make_text_response("Limite consultado.")]}
    mock_credit_factory.return_value = mock_credit

    supervisor = create_supervisor()
    state = initial_agent_state([HumanMessage(content="qual meu limite?")])
    state["target_agent"] = "credit"

    supervisor.invoke(state)

    mock_credit.invoke.assert_called_once()
    mock_triage_factory.return_value.invoke.assert_not_called()


@patch("src.agents.supervisor.create_triage_agent")
@patch("src.agents.supervisor.create_credit_agent")
@patch("src.agents.supervisor.create_interview_agent")
@patch("src.agents.supervisor.create_exchange_agent")
def test_supervisor_routes_to_exchange(
    mock_exchange_factory,
    mock_interview_factory,
    mock_credit_factory,
    mock_triage_factory,
):
    from src.agents.state import initial_agent_state
    from src.agents.supervisor import create_supervisor

    mock_exchange = MagicMock()
    mock_exchange.invoke.return_value = {"messages": [make_text_response("Cotação: R$ 5,15.")]}
    mock_exchange_factory.return_value = mock_exchange

    supervisor = create_supervisor()
    state = initial_agent_state([HumanMessage(content="cotação do dólar")])
    state["target_agent"] = "exchange"

    supervisor.invoke(state)

    mock_exchange.invoke.assert_called_once()


@patch("src.agents.supervisor.create_triage_agent")
@patch("src.agents.supervisor.create_credit_agent")
@patch("src.agents.supervisor.create_interview_agent")
@patch("src.agents.supervisor.create_exchange_agent")
def test_supervisor_defaults_to_triage(
    mock_exchange_factory,
    mock_interview_factory,
    mock_credit_factory,
    mock_triage_factory,
):
    from src.agents.state import initial_agent_state
    from src.agents.supervisor import create_supervisor

    mock_triage = MagicMock()
    mock_triage.invoke.return_value = {"messages": [make_text_response("Olá! Informe seu CPF.")]}
    mock_triage_factory.return_value = mock_triage

    supervisor = create_supervisor()
    state = initial_agent_state([HumanMessage(content="olá")])

    supervisor.invoke(state)

    mock_triage.invoke.assert_called_once()


@patch("src.agents.supervisor.create_triage_agent")
@patch("src.agents.supervisor.create_credit_agent")
@patch("src.agents.supervisor.create_interview_agent")
@patch("src.agents.supervisor.create_exchange_agent")
def test_supervisor_cascades_from_triage_to_credit(
    mock_exchange_factory,
    mock_interview_factory,
    mock_credit_factory,
    mock_triage_factory,
):
    from src.agents.state import initial_agent_state
    from src.agents.supervisor import create_supervisor

    mock_triage = MagicMock()
    mock_triage.invoke.return_value = {
        "messages": [make_text_response("Vou seguir com o atendimento de crédito.")],
        "target_agent": "credit",
        "authenticated": True,
    }
    mock_triage_factory.return_value = mock_triage

    mock_credit = MagicMock()
    mock_credit.invoke.return_value = {
        "messages": [make_text_response("Seu limite atual é R$ 2.500,00.")],
        "target_agent": "credit",
    }
    mock_credit_factory.return_value = mock_credit

    supervisor = create_supervisor()
    state = initial_agent_state([HumanMessage(content="quero consultar meu limite")])

    supervisor.invoke(state)

    mock_triage.invoke.assert_called_once()
    mock_credit.invoke.assert_called_once()


@patch("src.tools.credit.invoke_mcp_tool")
@patch("src.agents.credit.ChatBedrockConverse")
def test_credit_agent_consults_limit_e2e(mock_bedrock, mock_mcp, authenticated_credit_state):
    from src.agents.credit import create_credit_agent

    mock_llm = MagicMock()
    mock_bedrock.return_value = mock_llm
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = [
        make_tool_call_response("get_credit_limit", {"cpf": "12345678901"}),
        make_text_response("Seu limite atual é R$ 2.500,00."),
    ]

    mock_mcp.return_value = {
        "success": True,
        "current_limit": 2500.0,
        "max_allowed_limit": 3000.0,
        "score": 629.0,
        "message": "Limite consultado com sucesso.",
    }

    agent = create_credit_agent()
    result = agent.invoke(authenticated_credit_state)

    assert result["customer_limit"] == 2500.0
    assert mock_mcp.call_count == 1
    assert mock_llm.invoke.call_count == 2


@patch("src.tools.credit.invoke_mcp_tool")
@patch("src.agents.credit.ChatBedrockConverse")
def test_credit_agent_rejected_increase_sets_interview_flag(mock_bedrock, mock_mcp, authenticated_credit_state):
    from src.agents.credit import create_credit_agent

    authenticated_credit_state["messages"] = [HumanMessage(content="quero aumentar para 5000")]
    authenticated_credit_state["intent"] = "CREDIT_INCREASE"

    mock_llm = MagicMock()
    mock_bedrock.return_value = mock_llm
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = [
        make_tool_call_response(
            "request_credit_increase",
            {"cpf": "12345678901", "requested_limit": 5000.0},
        ),
        make_text_response("Infelizmente sua solicitação foi rejeitada."),
    ]

    mock_mcp.return_value = {
        "success": True,
        "status": "rejeitado",
        "new_limit": 2500.0,
        "message": "Solicitação rejeitada.",
    }

    agent = create_credit_agent()
    result = agent.invoke(authenticated_credit_state)

    assert result["last_request_status"] == "rejeitado"
    assert result["interview_offered"] is True


@patch("src.agents.interview.submit_collected_interview")
@patch("src.agents.interview.ChatBedrockConverse")
def test_interview_agent_records_answer_and_asks_next(
    mock_bedrock,
    mock_submit,
    authenticated_interview_state,
):
    from src.agents.interview import create_interview_agent

    mock_llm = MagicMock()
    mock_bedrock.return_value = mock_llm
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.return_value = make_tool_call_response(
        "record_interview_answer",
        {"field": "monthly_income", "value": "8000"},
    )

    agent = create_interview_agent()
    authenticated_interview_state["pending_user_input"] = "8000"
    result = agent.invoke(authenticated_interview_state)

    assert result["interview_collected"]["monthly_income"] == 8000.0
    assert result["interview_submitted"] is False
    assert result["interview_await_user"] is True
    mock_submit.assert_not_called()
    mock_llm.invoke.assert_called_once()


@patch("src.agents.interview.submit_collected_interview")
@patch("src.agents.interview.ChatBedrockConverse")
def test_interview_agent_completes_interview_and_redirects(
    mock_bedrock,
    mock_submit,
    authenticated_interview_state,
):
    from src.agents.interview import create_interview_agent

    mock_llm = MagicMock()
    mock_bedrock.return_value = mock_llm
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.return_value = make_tool_call_response(
        "record_interview_answer",
        {"field": "has_debts", "value": "não"},
    )

    mock_submit.return_value = {
        "success": True,
        "previous_score": 250.0,
        "new_score": 555.0,
        "message": "Entrevista registrada.",
    }

    authenticated_interview_state["interview_collected"] = {
        "monthly_income": 8000.0,
        "job_type": "formal",
        "monthly_expenses": 1500.0,
        "dependents": 0,
    }
    authenticated_interview_state["pending_user_input"] = "não"

    agent = create_interview_agent()
    result = agent.invoke(authenticated_interview_state)

    assert result["customer_score"] == 555.0
    assert result["target_agent"] == "credit"
    assert result["returned_from_interview"] is True
    assert result["interview_submitted"] is True
    mock_submit.assert_called_once()


@patch("src.tools.exchange.invoke_mcp_tool")
@patch("src.tools.session.invoke_mcp_tool")
@patch("src.agents.exchange.ChatBedrockConverse")
def test_exchange_agent_fetches_quote_and_ends(
    mock_bedrock,
    mock_session_mcp,
    mock_exchange_mcp,
    authenticated_exchange_state,
):
    from src.agents.exchange import create_exchange_agent

    mock_llm = MagicMock()
    mock_bedrock.return_value = mock_llm
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = [
        make_tool_call_response("get_currency_quote", {"currency": "USD"}),
        make_tool_call_response("end_conversation", {}, tool_call_id="call_2"),
        make_text_response("O dólar está cotado a R$ 5,15. Até logo!"),
    ]

    mock_exchange_mcp.return_value = {
        "success": True,
        "currency_code": "USD",
        "pair": "USD-BRL",
        "bid": 5.1523,
        "ask": 5.1545,
        "variation_pct": 0.35,
        "quoted_at": "2026-07-05 10:00:00",
        "message": "Cotação consultada com sucesso.",
    }
    mock_session_mcp.return_value = {
        "ended": True,
        "message": "Atendimento encerrado.",
    }

    agent = create_exchange_agent()
    result = agent.invoke(authenticated_exchange_state)

    assert result["conversation_ended"] is True
    assert mock_exchange_mcp.call_count == 1
    assert mock_session_mcp.call_count == 1
