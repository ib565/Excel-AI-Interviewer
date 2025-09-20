from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class Message(BaseModel):
    """Represents a single chat message in the transcript."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    turn_index: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class AIResponseWrapped(BaseModel):
    """Response returned by the AI adapter."""

    text: str
    metadata: Optional[Dict[str, Any]] = None
    end: bool = False


class AIResponse(BaseModel):
    """Response returned by the AI adapter."""

    text: str
    end: bool


class Question(BaseModel):
    """A single question from the optional bank."""

    id: str
    capability: List[str]  # Changed to List[str] to match JSON structure
    difficulty: str
    text: str
