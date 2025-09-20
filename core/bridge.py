from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List, Optional, Protocol

from core.models import AIResponseWrapped, Message


class AIAgent(Protocol):
    """Protocol that external AI modules must implement.

    The UI will pass prior messages and an optional state dict and expect an AIResponse.
    """

    @property
    def name(self) -> str:
        """Return a user-friendly name for this agent."""
        ...

    def generate_reply(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> AIResponseWrapped: ...


def load_ai_agent() -> AIAgent:
    """Load an AI agent from ai.agent if present, otherwise return a local stub.

    Expected external module contract:
    - File: ai/agent.py
    - Callable: get_agent() -> AIAgent
    """
    try:
        module = import_module("ai.agent")
        get_agent = getattr(module, "get_agent", None)
        print("get_agent")
        print(get_agent)
        if callable(get_agent):
            return get_agent()
    except Exception as e:
        print("load_ai_agent: Exception", e)
        # Fall back to local stub below
        print("load_ai_agent: Fall back to local stub")

    return _LocalEchoAgent()


class _LocalEchoAgent:
    """Simple built-in stub so the UI is testable without an AI agent."""

    @property
    def name(self) -> str:
        """Return user-friendly name for this agent."""
        return "Local Echo"

    def generate_reply(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> AIResponseWrapped:
        print("generate_reply")
        print(messages)
        print(state)
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        if last_user is None:
            return AIResponseWrapped(
                text="Hello! I'm a stubbed assistant. Tell me about your Excel skills.",
                metadata={"agent": "local_echo_stub"},
                end=False,
            )

        prefix = "Stub reply"
        name = None
        if isinstance(state, dict):
            name = state.get("candidate_name")
        if name:
            prefix = f"{prefix}, {name}"

        return AIResponseWrapped(
            text=f"{prefix}: I received your message — '{last_user.content}'.",
            metadata={"agent": "local_echo_stub"},
            end=False,
        )
