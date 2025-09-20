from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from google import genai
from google.genai import types
from core.models import AIResponseWrapped, Message, Question
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
        self.model = "gemini-2.5-flash"
        # Get access to the question bank
        self.question_bank = get_question_bank()
        # Track used questions in this session
        self._used_question_ids: Set[str] = set()
        # Set up logger
        self.logger = logging.getLogger("ai.adapter.gemini")

        def get_next_question(
            capabilities: List[str] = None,
            difficulty: str = None,
        ) -> Dict[str, Any]:
            """Retrieve the next question from the local bank.

            This function automatically avoids repeating questions within the current session.

            Args:
                capabilities: Optional list of capabilities to target (e.g., ["Formulas", "Pivot Tables"]).
                difficulty: Optional difficulty filter (e.g., "Easy", "Medium", "Hard", "Advanced").

            Returns:
                A dictionary with keys: id (str), text (str), difficulty (str), capabilities (List[str]).
            """
            print("in get_next_question")
            print(capabilities)
            print(difficulty)
            question = self._retrieve_question(
                capabilities=capabilities, difficulty=difficulty
            )
            if question is None:
                return {
                    "id": "",
                    "text": "No more suitable questions are available.",
                    "difficulty": difficulty or "",
                    "capabilities": capabilities or [],
                }

            # Mark question as used immediately to avoid repeats
            if question.id:
                self._used_question_ids.add(question.id)

            return {
                "id": question.id,
                "text": question.text,
                "difficulty": question.difficulty,
                "capabilities": question.capabilities,
            }

        # Register available tools for function calling
        self._tools = [get_next_question]

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
            # Call Gemini API with function-calling tools (no structured outputs)
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(tools=self._tools),
            )

            # Log the raw API response
            self.logger.debug(
                "LLM_RAW_RESPONSE | %s",
                json.dumps(response.model_dump(), indent=2, default=str),
            )

            # Extract response text
            reply_text_raw: str = getattr(response, "text", "").strip()

            # Parse flags from the response tail and clean them from user-visible text
            cleaned_text, end_flag, question_id_from_flags = (
                self._parse_flags_and_clean_text(reply_text_raw)
            )

            # If model explicitly referenced a question id, track it
            if question_id_from_flags:
                self._used_question_ids.add(question_id_from_flags)

            # Determine end condition using flag or heuristic
            should_end = bool(end_flag) or self._should_end_interview(messages)

            # Create the wrapped response
            wrapped_response = AIResponseWrapped(
                text=cleaned_text,
                metadata={
                    "adapter": "gemini",
                    "model": self.model,
                    "tokens_used": getattr(response, "usage", {}).get(
                        "total_tokens", 0
                    ),
                    "questions_used": len(self._used_question_ids),
                    "question_id": question_id_from_flags,
                },
                end=should_end,
            )

            # Log the final wrapped response details
            self.logger.info(
                "LLM_RESPONSE | text=%s | end=%s | tokens_used=%s | metadata=%s",
                cleaned_text,
                should_end,
                wrapped_response.metadata.get("tokens_used", 0),
                json.dumps(wrapped_response.metadata, default=str),
            )

            # Log the raw text for debugging
            self.logger.debug("LLM_TEXT | %s", reply_text_raw)

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
        prompt = (
            "You are an expert Excel interviewer conducting a mock interview.\n"
            "Your goal is to assess the candidate's Excel skills through conversation.\n\n"
            "Guidelines:\n"
            "- Ask specific, technical Excel questions using the available tool when needed.\n"
            "- Follow up on their answers with clarifying questions.\n"
            "- Be conversational but professional.\n"
            "- End the interview after max 10 questions or when appropriate.\n\n"
            "Tool-use contract:\n"
            "- When you need a new question, CALL the function get_next_question(capabilities?, difficulty?).\n"
            "- After composing your reply for the candidate, append a single flags line EXACTLY in this form: \n"
            "  [[END=<true|false> QID=<question_id or none>]]\n"
            "- Do not include the flags in the visible body of your message; put them only at the very end.\n\n"
        )

        # Add question bank context
        question_count = self.question_bank.get_question_count()
        if question_count > 0:
            available_capabilities = self.question_bank.get_available_capabilities()
            available_difficulties = self.question_bank.get_available_difficulties()

            prompt += (
                f"Available questions: {question_count}\n"
                f"Capabilities: {', '.join(available_capabilities)}\n"
                f"Difficulty levels: {', '.join(available_difficulties)}\n\n"
                "Selection guidance:\n"
                "- Start with easier questions and progress to harder ones.\n"
                "- Choose questions that build on the candidate's previous answers.\n"
                "- Avoid repeating questions within the same interview.\n"
            )

        # Add context from state if available
        if state:
            session_id = state.get("session_id")
            if session_id:
                prompt += f"\n- Session ID: {session_id}"

        return prompt

    def _should_end_interview(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Determine if the interview should end."""

        # End after several exchanges
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if len(assistant_messages) >= 10:  # End after 10 AI responses
            return True

        # Check state for end condition
        if state and state.get("force_end", False):
            return True

        return False

    def _retrieve_question(
        self, capabilities: Optional[List[str]] = None, difficulty: Optional[str] = None
    ) -> Optional[Question]:
        """Retrieve a question from the question bank."""
        print("retrieve_question")
        return self.question_bank.select_random_question(
            exclude_ids=self._used_question_ids,
            capabilities=capabilities,
            difficulty=difficulty,
        )

    def _parse_flags_and_clean_text(self, text: str) -> Tuple[str, bool, Optional[str]]:
        """Extract end/QID flags from the response tail and return cleaned text.

        The protocol expects a trailing token like: [[END=true QID=123]]
        Returns (cleaned_text, end_flag, question_id)
        """
        if not text:
            return "", False, None

        # Regex to capture flags block at the end
        flags_pattern = re.compile(
            r"\s*\[\[\s*END\s*=\s*(true|false)\s+QID\s*=\s*([^\]]+)\s*\]\]\s*$",
            re.IGNORECASE,
        )
        match = flags_pattern.search(text)
        if not match:
            return text, False, None

        end_str = match.group(1).lower()
        qid_raw = match.group(2).strip()
        end_flag = end_str == "true"
        question_id = None if qid_raw in {"none", "", "null"} else qid_raw

        # Remove the flags block from the text
        cleaned = text[: match.start()].rstrip()
        return cleaned, end_flag, question_id


def get_adapter() -> AIAdapter:
    """Factory function that returns the Gemini adapter.

    This function signature is part of the Protocol contract.
    The Protocol ensures that whatever this returns implements
    the AIAdapter interface.
    """
    return GeminiAdapter()
