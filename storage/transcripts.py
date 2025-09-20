from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import get_session_transcript_path


def _ensure_parent(path_str: str) -> None:
    Path(path_str).parent.mkdir(parents=True, exist_ok=True)


def append_jsonl_line(path_str: str, obj: Dict[str, Any]) -> None:
    _ensure_parent(path_str)
    with open(path_str, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def save_message_line(
    session_id: str,
    role: str,
    content: str,
    turn_index: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    entry: Dict[str, Any] = {
        "type": "message",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content,
    }
    if turn_index is not None:
        entry["turn_index"] = turn_index
    if metadata:
        entry["metadata"] = metadata
    append_jsonl_line(get_session_transcript_path(session_id), entry)


def save_event_line(
    session_id: str,
    event: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    entry: Dict[str, Any] = {
        "type": "event",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    if details:
        entry["details"] = details
    append_jsonl_line(get_session_transcript_path(session_id), entry)


def load_transcript(session_id: str) -> List[Dict[str, Any]]:
    path_str = get_session_transcript_path(session_id)
    path = Path(path_str)
    if not path.exists():
        return []
    lines: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except Exception:
                continue
    return lines
