from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

import streamlit as st

from config import (
    APP_NAME,
    LOGS_DIR,
    QUESTION_BANK_PATH,
    ensure_app_dirs,
    get_session_log_path,
    get_session_transcript_path,
)
from core.bridge import load_ai_agent
from core.models import AIResponseWrapped, Message
from storage.transcripts import save_event_line, save_message_line
from storage.question_bank import get_question_bank

# Configure root logger to reduce console clutter for submission
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        # File handler for all logs
        logging.FileHandler(LOGS_DIR / "application.log", encoding="utf-8"),
        # Console handler with reduced verbosity
        logging.StreamHandler(),
    ],
)
# Set console handler to WARNING level for cleaner terminal output
logging.getLogger().handlers[1].setLevel(logging.WARNING)


st.set_page_config(page_title=APP_NAME, layout="wide")


def _init_session_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ended" not in st.session_state:
        st.session_state.ended = False
    if "turn_index" not in st.session_state:
        st.session_state.turn_index = 0
    if "evaluation_generated" not in st.session_state:
        st.session_state.evaluation_generated = False
    if "performance_summary" not in st.session_state:
        st.session_state.performance_summary = None


def _get_logger() -> logging.Logger:
    # Get the main session logger
    logger = logging.getLogger(f"session.{st.session_state.session_id}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Create timestamp for filename sorting (ISO format without colons)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        fh = logging.FileHandler(
            get_session_log_path(st.session_state.session_id, timestamp),
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Console handler with reduced verbosity for clean terminal output
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)  # Only show warnings and errors in console
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)

        # Set up the AI agent logger with file-only logging
        ai_logger = logging.getLogger("ai.agent.gemini")
        if not ai_logger.handlers:
            ai_logger.setLevel(logging.INFO)  # Reduced from DEBUG for cleaner output
            ai_logger.addHandler(fh)  # Use the same file handler
            # Remove console handler for AI agent to reduce terminal clutter
            ai_logger.propagate = False  # Prevent duplicate logs

    return logger


def _append_message(
    role: str, content: str, metadata: Dict[str, Any] | None = None
) -> None:
    msg = Message(
        role=role,
        content=content,
        timestamp=datetime.now(timezone.utc),
        turn_index=st.session_state.turn_index,
        metadata=metadata,
    )
    st.session_state.messages.append(msg.model_dump())
    save_message_line(
        session_id=st.session_state.session_id,
        role=role,
        content=content,
        turn_index=st.session_state.turn_index,
        metadata=metadata,
    )
    st.session_state.turn_index += 1


def _render_header() -> None:
    st.title(APP_NAME)
    st.caption(
        "Conversational Excel interviewer. Retrieves questions from a dynamic question bank, and evaluates the candidate's responses. Generates a performance summary at the end.\n"
    )
    st.caption(
        "The user can ask to end the interview at any time. The Agent has been instructed to keep the interview short for demo purposes."
    )


def _render_sidebar(agent_name: str) -> None:
    with st.sidebar:
        st.subheader("Interview Controls")
        st.text(f"Agent: {agent_name}")

        if st.button("Restart session", width="stretch"):
            _restart_session()
            st.rerun()

        # Display question bank info
        question_bank = get_question_bank()
        with st.expander("Question bank (sample)", expanded=False):
            question_count = question_bank.get_question_count()
            if question_count > 0:
                st.info(f"Total questions: {question_count}")

                # Show sample questions
                sample_questions = question_bank.select_questions(
                    min(3, question_count)
                )
                for q in sample_questions:
                    st.write(
                        f"**{q.capabilities}** ({q.difficulty}): {q.text[:100]}..."
                    )
            else:
                st.info("No question bank found.")

        if st.session_state.messages:
            _transcript_download()


def _restart_session() -> None:
    old_session = st.session_state.session_id
    save_event_line(session_id=old_session, event="restart", details=None)
    st.session_state.session_id = str(uuid4())
    st.session_state.messages = []
    st.session_state.ended = False
    st.session_state.turn_index = 0
    st.session_state.evaluation_generated = False
    st.session_state.performance_summary = None


def _transcript_download() -> None:
    try:
        # Use current session state messages instead of loading from disk
        # to ensure we get the most up-to-date transcript
        cleaned_transcript = []
        for message in st.session_state.messages:
            role = message.get("role", "").title()
            content = message.get("content", "")
            cleaned_transcript.append(f"{role}: {content}")

        # Join with double newlines for readability
        data = "\n\n".join(cleaned_transcript)

        st.download_button(
            label="Download transcript (.txt)",
            data=data,
            file_name=f"transcript_{st.session_state.session_id}.txt",
            mime="text/plain",
            width="stretch",
        )
    except Exception:
        st.warning("Transcript not available yet.")


def _to_model_messages(raw_messages: List[Dict[str, Any]]) -> List[Message]:
    return [Message(**m) for m in raw_messages]


def _maybe_bootstrap_first_message() -> None:
    if not st.session_state.messages and not st.session_state.ended:
        content = (
            "To kick off, please share a brief self-assessment of your Excel skills, "
            "experience, and comfort areas."
        )
        save_event_line(st.session_state.session_id, "bootstrap", details=None)
        _append_message("assistant", content)


def main() -> None:
    ensure_app_dirs()
    _init_session_state()

    # Only show startup message once per session
    if "startup_logged" not in st.session_state:
        logger = _get_logger()
        agent = load_ai_agent()
        agent_name = agent.name

        # Log startup info for submission visibility
        print(f"🚀 Excel Interviewer AI started successfully with agent: {agent_name}")
        logger.info("Application started with agent: %s", agent_name)
        st.session_state.startup_logged = True
        st.session_state.agent = agent
        st.session_state.agent_name = agent_name
    else:
        logger = _get_logger()
        agent = st.session_state.agent
        agent_name = st.session_state.agent_name

    _render_header()
    _render_sidebar(agent_name)

    _maybe_bootstrap_first_message()

    # Handle input BEFORE rendering the transcript to avoid one-message lag
    user_input = st.chat_input("Your message", disabled=st.session_state.ended)
    if user_input and not st.session_state.ended:
        # User message logged to file only (not console for clean output)
        _append_message("user", user_input)

        state: Dict[str, Any] = {
            "session_id": st.session_state.session_id,
        }
        try:
            response: AIResponseWrapped = agent.generate_reply(
                _to_model_messages(st.session_state.messages), state
            )
        except Exception as e:
            logger.error("agent_error | %s", str(e))
            logger.debug(
                "agent_error_details | %s",
                json.dumps(
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "session_id": st.session_state.session_id,
                    },
                    indent=2,
                ),
            )
            response = AIResponseWrapped(text="Agent error: using fallback reply.")

        # Log assistant response to file only (not console for clean output)
        logger.debug(
            "assistant_message | text=%s | end=%s | metadata=%s",
            response.text[:100] + "..." if len(response.text) > 100 else response.text,
            response.end,
            json.dumps(response.metadata or {}, default=str),
        )

        _append_message("assistant", response.text, metadata=response.metadata)

        if response.end:
            st.session_state.ended = True
            save_event_line(st.session_state.session_id, "end", details=None)

            # Generate performance summary if not already generated
            if not st.session_state.evaluation_generated:
                try:
                    st.session_state.performance_summary = (
                        agent.generate_performance_summary(
                            _to_model_messages(st.session_state.messages)
                        )
                    )
                    st.session_state.evaluation_generated = True
                    save_event_line(
                        st.session_state.session_id,
                        "evaluation_generated",
                        details=None,
                    )
                except Exception as e:
                    logger.error("Failed to generate performance summary: %s", str(e))
                    st.session_state.performance_summary = (
                        "## Performance Evaluation Error\n\n"
                        "We encountered an error while generating the performance summary. "
                        "Please review the transcript manually for assessment."
                    )
                    st.session_state.evaluation_generated = True

            # Force immediate rerun to apply disabled state to input
            st.rerun()

    # Now render the transcript AFTER handling input
    container = st.container()
    with container:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

    # Show success popup and performance summary AFTER transcript rendering to ensure it's visible
    if st.session_state.ended:
        st.success(
            "This interview session has ended. You can download the transcript or restart."
        )

        # Display performance summary if available
        if st.session_state.performance_summary:
            st.markdown("---")
            st.subheader("📊 Performance Summary")
            st.markdown(st.session_state.performance_summary)


if __name__ == "__main__":
    main()
