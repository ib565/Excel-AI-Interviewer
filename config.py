import os
from pathlib import Path


APP_NAME = "Excel Interviewer AI"


BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
QUESTION_BANK_PATH = DATA_DIR / "question_bank.json"


def ensure_app_dirs() -> None:
    """Create required application directories if missing."""
    for directory in (TRANSCRIPTS_DIR, LOGS_DIR, DATA_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def get_session_log_path(session_id: str) -> str:
    """Return absolute log file path for a session id."""
    return str(LOGS_DIR / f"{session_id}.log")


def get_session_transcript_path(session_id: str) -> str:
    """Return absolute transcript file path for a session id."""
    return str(TRANSCRIPTS_DIR / f"{session_id}.jsonl")
