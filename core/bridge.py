from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List, Optional, Protocol

from core.models import AIResponseWrapped, Message


class AIAdapter(Protocol):
    """Protocol that external AI modules must implement.

    The UI will pass prior messages and an optional state dict and expect an AIResponse.
    """

    @property
    def name(self) -> str:
        """Return a user-friendly name for this adapter."""
        ...

    def generate_reply(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> AIResponseWrapped: ...


def load_ai_adapter() -> AIAdapter:
    """Load an AI adapter from ai.adapter if present, otherwise return a local stub.

    Expected external module contract:
    - File: ai/adapter.py
    - Callable: get_adapter() -> AIAdapter
    """
    try:
        module = import_module("ai.adapter")
        get_adapter = getattr(module, "get_adapter", None)
        print("get_adapter")
        print(get_adapter)
        if callable(get_adapter):
            return get_adapter()
    except Exception as e:
        print("load_ai_adapter: Exception", e)
        # Fall back to local stub below
        print("load_ai_adapter: Fall back to local stub")

    return _LocalEchoAdapter()


class _LocalEchoAdapter:
    """Simple built-in stub so the UI is testable without an AI backend."""

    @property
    def name(self) -> str:
        """Return user-friendly name for this adapter."""
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
                metadata={"adapter": "local_echo_stub"},
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
            metadata={"adapter": "local_echo_stub"},
            end=False,
        )
