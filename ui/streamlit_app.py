import asyncio
import logging
import os
import sys
import uuid


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


from src.agents.state import initial_agent_state
from src.agents.supervisor import supervisor_agent
from src.utils import configure_logging


load_dotenv(override=True)

configure_logging()
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Banco Ágil - Atendimento Inteligente",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ecf0f1;
    }
    .status-container {
        padding: 10px;
        border-radius: 5px;
        background-color: #1e293b;
        margin-bottom: 15px;
        border: 1px solid #334155;
    }
    .status-dot {
        height: 10px;
        width: 10px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    .tool-tag {
        display: inline-block;
        background-color: #3b82f6;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        margin: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "agent_state" not in st.session_state:
    st.session_state.agent_state = initial_agent_state()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


def get_mcp_tools() -> list[str]:
    async def _fetch():
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            env=dict(os.environ),
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_list = await session.list_tools()
                return [t.name for t in tools_list.tools]

    try:
        return asyncio.run(_fetch())
    except Exception as exc:
        logger.error("Falha ao listar ferramentas MCP: %s", exc)
        return [f"Erro: {exc}"]


st.sidebar.title("Configurações & MCP")
st.sidebar.markdown("---")

with st.sidebar.status("Conectando ao Servidor MCP...", expanded=True) as status_box:
    mcp_tools = get_mcp_tools()
    status_box.update(label="Conectado ao Servidor MCP", state="complete")

st.sidebar.markdown(
    """
    <div class="status-container">
        <span class="status-dot"></span>
        <strong>Servidor MCP:</strong> Ativo (Stdio)
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.subheader("Ferramentas MCP Disponíveis")
if mcp_tools:
    for tool_name in mcp_tools:
        st.sidebar.markdown(
            f'<span class="tool-tag">{tool_name}</span>',
            unsafe_allow_html=True,
        )
else:
    st.sidebar.warning("Nenhuma ferramenta encontrada.")

st.sidebar.markdown("---")
st.sidebar.caption("Estado da sessão")
st.sidebar.write(f"Autenticado: {'Sim' if st.session_state.agent_state.get('authenticated') else 'Não'}")
st.sidebar.write(f"Tentativas de auth: {st.session_state.agent_state.get('auth_attempts', 0)}")
if st.session_state.agent_state.get("last_request_status"):
    st.sidebar.write(f"Último pedido: {st.session_state.agent_state['last_request_status']}")

if st.sidebar.button("🔄 Reiniciar Conversa"):
    st.session_state.agent_state = initial_agent_state()
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()


st.title("🏦 Lican - Portal Banco Ágil")
st.markdown(
    "Bem-vindo ao canal de atendimento do Banco Ágil. "
    "Sou o **Lican**, seu assistente virtual."
)


def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif "text" in part and part.get("type") != "reasoning_content":
                    text_parts.append(part["text"])
        return "".join(text_parts).strip()
    return str(content)


for message in st.session_state.agent_state.get("messages", []):
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.write(message.content)
    elif isinstance(message, AIMessage):
        msg_text = extract_text_content(message.content)
        if msg_text:
            with st.chat_message("assistant"):
                st.write(msg_text)


def process_message(prompt: str) -> None:
    tid = st.session_state.thread_id
    logger.info(
        "Nova mensagem recebida — %d chars",
        len(prompt),
        extra={"thread_id": tid},
    )

    user_msg = HumanMessage(content=prompt)
    current_state = dict(st.session_state.agent_state)
    current_state["messages"] = current_state.get("messages", []) + [user_msg]

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()

        try:
            response = supervisor_agent.invoke(
                current_state,
                config={"configurable": {"thread_id": tid}},
            )

            st.session_state.agent_state = response

            last_ai_content = next(
                (
                    m.content
                    for m in reversed(response.get("messages", []))
                    if isinstance(m, AIMessage) and m.content
                ),
                "Entendido. Processando sua solicitação...",
            )
            last_ai_msg = extract_text_content(last_ai_content)
            placeholder.markdown(last_ai_msg)

        except Exception as exc:
            logger.error(
                "Erro ao processar mensagem: %s",
                exc,
                exc_info=True,
                extra={"thread_id": tid},
            )
            error_msg = f"Desculpe, ocorreu um erro ao processar sua solicitação: {exc}"
            placeholder.error(error_msg)
            current_state["messages"].append(AIMessage(content=error_msg))
            st.session_state.agent_state = current_state


if user_input := st.chat_input(
    "Digite sua mensagem aqui...",
    disabled=st.session_state.agent_state.get("conversation_ended", False),
):
    process_message(user_input)

if st.session_state.agent_state.get("conversation_ended"):
    st.info("Atendimento encerrado. Clique em **Reiniciar Conversa** para iniciar um novo atendimento.")
