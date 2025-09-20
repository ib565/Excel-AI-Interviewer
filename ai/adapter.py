from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set
from google import genai
from core.models import AIResponse, Message
from core.bridge import AIAdapter
from storage.question_bank import get_question_bank


class GeminiAdapter:
    """Gemini-based AI adapter implementing the AIAdapter Protocol.

    This demonstrates how the Protocol pattern allows clean separation
    between the interface contract and the implementation.
    """

    @property
    def name(self) -> str:
        """Return user-friendly name for this adapter."""
        return "Gemini AI"

    def __init__(self):
        # Initialize Gemini client (you'd set GEMINI_API_KEY in environment)
        self.client = genai.Client()
        self.model = "gemini-2.5-flash"
        # Get access to the question bank
        self.question_bank = get_question_bank()
        # Track used questions in this session
        self._used_question_ids: Set[str] = set()

    def generate_reply(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> AIResponse:
        """Generate a response using Gemini AI.

        This method signature MUST match the AIAdapter Protocol exactly.
        The Protocol ensures type safety and interface consistency.
        """

        # Convert messages to Gemini format
        gemini_messages = self._convert_messages_to_gemini_format(messages)

        # Build the system prompt based on interview context
        system_prompt = self._build_system_prompt(state)

        # Prepare the full prompt
        full_prompt = f"{system_prompt}\n\nConversation:\n" + "\n".join(gemini_messages)

        try:
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model, contents=full_prompt
            )

            # Extract response text
            reply_text = response.text.strip()

            # Check if interview should end based on context
            should_end = self._should_end_interview(messages, state)

            return AIResponse(
                text=reply_text,
                metadata={
                    "adapter": "gemini",
                    "model": self.model,
                    "tokens_used": getattr(response, "usage", {}).get(
                        "total_tokens", 0
                    ),
                    "questions_used": len(self._used_question_ids),
                },
                end=should_end,
            )

        except Exception as e:
            # Fallback response if Gemini fails
            return AIResponse(
                text=f"I apologize, but I'm having trouble connecting to Gemini right now. Error: {str(e)}",
                metadata={"adapter": "gemini", "error": str(e)},
                end=False,
            )

    def _convert_messages_to_gemini_format(self, messages: List[Message]) -> List[str]:
        """Convert internal Message objects to Gemini conversation format."""
        formatted_messages = []
        for msg in messages:
            role = "user" if msg.role == "user" else "assistant"
            formatted_messages.append(f"{role}: {msg.content}")
        return formatted_messages

    def _build_system_prompt(self, state: Optional[Dict[str, Any]]) -> str:
        """Build a system prompt based on the interview state."""

        # Base system prompt
        prompt = """You are an expert Excel interviewer conducting a mock interview.
        Your goal is to assess the candidate's Excel skills through conversation.
        
        Guidelines:
        - Ask specific, technical Excel questions from the provided question bank
        - Follow up on their answers with clarifying questions
        - Be conversational but professional
        - End the interview after 3-5 questions or when appropriate
        
        When selecting questions:
        - Start with easier questions and progress to harder ones
        - Choose questions that build on the candidate's previous answers
        - Avoid repeating questions within the same interview
        """

        # Add question bank context
        question_count = self.question_bank.get_question_count()
        if question_count > 0:
            available_capabilities = self.question_bank.get_available_capabilities()
            available_difficulties = self.question_bank.get_available_difficulties()

            prompt += f"""
            
Available questions: {question_count}
Capabilities: {', '.join(available_capabilities)}
Difficulty levels: {', '.join(available_difficulties)}

Select appropriate questions based on:
- The candidate's demonstrated skill level
- Previous conversation context
- Question difficulty progression
- Available question variety
"""

        # Add context from state if available
        if state:
            session_id = state.get("session_id")
            if session_id:
                prompt += f"\n- Session ID: {session_id}"

        return prompt

    def _should_end_interview(
        self, messages: List[Message], state: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if the interview should end."""

        # End after several exchanges
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if len(assistant_messages) >= 4:  # End after 4 AI responses
            return True

        # Check state for end condition
        if state and state.get("force_end", False):
            return True

        return False


def get_adapter() -> AIAdapter:
    """Factory function that returns the Gemini adapter.

    This function signature is part of the Protocol contract.
    The Protocol ensures that whatever this returns implements
    the AIAdapter interface.
    """
    return GeminiAdapter()
