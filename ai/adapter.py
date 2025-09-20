from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set
from google import genai
from core.models import AIResponseWrapped, Message, Question, AIResponse
from core.bridge import AIAdapter
from storage.question_bank import get_question_bank
from dotenv import load_dotenv

load_dotenv()


class GeminiAdapter:
    """Gemini-based AI adapter implementing the AIAdapter Protocol."""

    @property
    def name(self) -> str:
        """Return user-friendly name for this adapter."""
        return "Gemini AI"

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash"
        # Get access to the question bank
        self.question_bank = get_question_bank()
        # Track used questions in this session
        self._used_question_ids: Set[str] = set()
        # Set up logger
        self.logger = logging.getLogger("ai.adapter.gemini")

    def generate_reply(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> AIResponseWrapped:
        """Generate a response using Gemini AI.

        This method signature MUST match the AIAdapter Protocol exactly.
        The Protocol ensures type safety and interface consistency.
        """

        # Convert messages to Gemini format
        gemini_messages = self._convert_messages_to_gemini_format(messages)

        # Build the system prompt based on interview context
        system_prompt = self._build_system_prompt()

        # Prepare the full prompt
        full_prompt = f"{system_prompt}\n\nConversation:\n" + "\n".join(gemini_messages)

        # Log the full prompt being sent to LLM
        self.logger.debug("LLM_REQUEST | prompt=%s", full_prompt)
        self.logger.info(
            "LLM_REQUEST | message_count=%d | prompt_length=%d",
            len(messages),
            len(full_prompt),
        )

        try:
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": AIResponse,
                },
            )

            # Log the raw API response
            self.logger.debug(
                "LLM_RAW_RESPONSE | %s",
                json.dumps(response.model_dump(), indent=2, default=str),
            )

            response_parsed = response.parsed

            # Extract response text
            reply_text = response_parsed.text.strip()

            # Check if interview should end based on context
            should_end = response_parsed.end

            # Create the wrapped response
            wrapped_response = AIResponseWrapped(
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

            # Log the final wrapped response details
            self.logger.info(
                "LLM_RESPONSE | text=%s | end=%s | tokens_used=%s | metadata=%s",
                reply_text,
                should_end,
                wrapped_response.metadata.get("tokens_used", 0),
                json.dumps(wrapped_response.metadata, default=str),
            )

            # Log the parsed response object details
            self.logger.debug(
                "LLM_PARSED_RESPONSE | %s",
                json.dumps(response_parsed.model_dump(), indent=2),
            )

            return wrapped_response

        except Exception as e:
            # Log the error details
            self.logger.error("LLM_ERROR | %s", str(e))
            self.logger.debug(
                "LLM_ERROR_DETAILS | %s",
                json.dumps(
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "prompt_length": (
                            len(full_prompt) if "full_prompt" in locals() else 0
                        ),
                        "message_count": len(messages),
                    },
                    indent=2,
                ),
            )

            # Fallback response if Gemini fails
            return AIResponseWrapped(
                text=f"I apologize, but I'm having trouble connecting to Gemini right now. Error: {str(e)}",
                metadata={
                    "adapter": "gemini",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                end=False,
            )

    def _convert_messages_to_gemini_format(self, messages: List[Message]) -> List[str]:
        """Convert internal Message objects to Gemini conversation format."""
        formatted_messages = []
        for msg in messages:
            role = "user" if msg.role == "user" else "assistant"
            formatted_messages.append(f"{role}: {msg.content}")
        return formatted_messages

    def _build_system_prompt(self, state: Optional[Dict[str, Any]] = None) -> str:
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

        prompt = """You are an Excel Interviewer conducting an interview.
        Your goal is to assess the candidate's Excel skills through conversation.
        """

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

    def _retrieve_question(
        self, capabilities: Optional[List[str]] = None, difficulty: Optional[str] = None
    ) -> Optional[Question]:
        """Retrieve a question from the question bank."""
        return self.question_bank.select_random_question(
            exclude_ids=self._used_question_ids,
            capabilities=capabilities,
            difficulty=difficulty,
        )


def get_adapter() -> AIAdapter:
    """Factory function that returns the Gemini adapter.

    This function signature is part of the Protocol contract.
    The Protocol ensures that whatever this returns implements
    the AIAdapter interface.
    """
    print("ai/adapter.py: get_adapter")
    return GeminiAdapter()
