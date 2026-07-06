import logging
import os
import sys
import uuid


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

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
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
        color: #0f172a;
    }
    #MainMenu {
        visibility: hidden;
    }
    footer {
        visibility: hidden;
    }
    section[data-testid="stSidebar"] {
        display: none;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    div.block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    .app-shell {
        max-width: 1100px;
        margin: 0 auto;
    }
    .hero {
        padding: 1.25rem 1.5rem;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(10px);
        margin-bottom: 1rem;
    }
    .hero h1 {
        color: #0f172a;
        font-size: 2rem;
        margin-bottom: 0.35rem;
    }
    .hero p {
        color: #334155;
        margin-bottom: 0;
    }
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.96);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 18px;
        padding: 0.5rem 0.75rem;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        color: #0f172a;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div {
        color: #0f172a !important;
    }
    [data-testid="stChatMessage"][aria-label="user"] {
        background: linear-gradient(180deg, #eff6ff 0%, #e0efff 100%);
    }
    [data-testid="stChatMessage"][aria-label="assistant"] {
        background: rgba(255, 255, 255, 0.98);
    }
    [data-testid="stChatInput"] textarea {
        background: rgba(255, 255, 255, 0.96);
        color: #0f172a;
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 14px;
    }
    [data-testid="stButton"] button {
        border-radius: 999px;
        border: 1px solid rgba(59, 130, 246, 0.2);
        background: #ffffff;
        color: #1d4ed8;
        font-weight: 600;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "agent_state" not in st.session_state:
    st.session_state.agent_state = initial_agent_state()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


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


def render_history() -> None:
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

    if not prompt.strip():
        return

    current_state = dict(st.session_state.agent_state)
    current_state["pending_user_input"] = prompt

    try:
        with st.spinner("Processando atendimento..."):
            response = supervisor_agent.invoke(
                current_state,
                config={"configurable": {"thread_id": tid}},
            )

        st.session_state.agent_state = response
        st.rerun()

    except Exception as exc:
        logger.error(
            "Erro ao processar mensagem: %s",
            exc,
            exc_info=True,
            extra={"thread_id": tid},
        )
        error_msg = f"Desculpe, ocorreu um erro ao processar sua solicitação: {exc}"
        current_state["pending_user_input"] = None
        current_state["messages"].append(AIMessage(content=error_msg))
        st.session_state.agent_state = current_state
        st.rerun()


with st.container():
    header_left, header_right = st.columns([6, 1])
    with header_left:
        st.markdown(
            """
            <div class="hero">
                <h1>Banco Ágil</h1>
                <p>Atendimento em tela cheia com o assistente Lican.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with header_right:
        st.write("")
        if st.button("Reiniciar conversa", use_container_width=True):
            st.session_state.agent_state = initial_agent_state()
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

    render_history()

    if user_input := st.chat_input(
        "Digite sua mensagem aqui...",
        disabled=st.session_state.agent_state.get("conversation_ended", False),
    ):
        process_message(user_input)

    if st.session_state.agent_state.get("conversation_ended"):
        st.info("Atendimento encerrado. Clique em Reiniciar conversa para iniciar um novo atendimento.")
