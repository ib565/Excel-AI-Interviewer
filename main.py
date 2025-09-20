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
    QUESTION_BANK_PATH,
    ensure_app_dirs,
    get_session_log_path,
    get_session_transcript_path,
)
from core.bridge import load_ai_adapter
from core.models import AIResponseWrapped, Message
from storage.transcripts import save_event_line, save_message_line
from storage.question_bank import get_question_bank


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

        # Also add console handler for debugging
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # Set up the AI adapter logger
    ai_logger = logging.getLogger("ai.adapter.gemini")
    if not ai_logger.handlers:
        ai_logger.setLevel(logging.DEBUG)  # More detailed logging for AI adapter
        ai_logger.addHandler(fh)  # Use the same file handler
        ai_logger.addHandler(ch)  # Use the same console handler
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
        "Proof-of-concept: conversational Excel interviewer. AI adapter is pluggable."
    )


def _render_sidebar(adapter_name: str) -> None:
    with st.sidebar:
        st.subheader("Interview Controls")
        st.text(f"Adapter: {adapter_name}")

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


def _transcript_download() -> None:
    path = get_session_transcript_path(st.session_state.session_id)
    try:
        data = Path(path).read_text(encoding="utf-8")
        st.download_button(
            label="Download transcript (.jsonl)",
            data=data,
            file_name=f"transcript_{st.session_state.session_id}.jsonl",
            mime="application/json",
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
    logger = _get_logger()
    adapter = load_ai_adapter()
    adapter_name = adapter.name

    _render_header()
    _render_sidebar(adapter_name)

    _maybe_bootstrap_first_message()

    # Handle input BEFORE rendering the transcript to avoid one-message lag
    user_input = st.chat_input("Your message", disabled=st.session_state.ended)
    if user_input and not st.session_state.ended:
        logger.info("user_message | %s", user_input)
        _append_message("user", user_input)

        state: Dict[str, Any] = {
            "session_id": st.session_state.session_id,
        }
        try:
            response: AIResponseWrapped = adapter.generate_reply(
                _to_model_messages(st.session_state.messages), state
            )
        except Exception as e:
            logger.error("adapter_error | %s", str(e))
            logger.debug(
                "adapter_error_details | %s",
                json.dumps(
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "session_id": st.session_state.session_id,
                    },
                    indent=2,
                ),
            )
            response = AIResponseWrapped(text="Adapter error: using fallback reply.")

        # Log the full assistant response details
        logger.info(
            "assistant_message | text=%s | end=%s | metadata=%s",
            response.text,
            response.end,
            json.dumps(response.metadata or {}, default=str),
        )
        logger.debug(
            "assistant_full_response | %s",
            json.dumps(response.model_dump(), indent=2, default=str),
        )

        _append_message("assistant", response.text, metadata=response.metadata)

        if response.end:
            st.session_state.ended = True
            save_event_line(st.session_state.session_id, "end", details=None)
            # Force immediate rerun to apply disabled state to input
            st.rerun()

    # Now render the transcript AFTER handling input
    container = st.container()
    with container:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

    # Show success popup AFTER transcript rendering to ensure it's visible
    if st.session_state.ended:
        st.success(
            "This interview session has ended. You can download the transcript or restart."
        )


if __name__ == "__main__":
    main()
