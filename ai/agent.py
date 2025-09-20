import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from google import genai
from google.genai import types
from core.models import AIResponseWrapped, Message, Question
from core.bridge import AIAgent
from core.utils import parse_response_flags_and_clean_text
from storage.question_bank import get_question_bank
from ai.prompts import (
    render_system_prompt,
    render_generate_question_prompt,
    render_performance_evaluation_prompt,
)
from dotenv import load_dotenv

load_dotenv()


class GeminiAgent:
    """Gemini-based AI agent implementing the AIAgent Protocol."""

    @property
    def name(self) -> str:
        """Return user-friendly name for this agent."""
        return "Gemini AI"

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("MODEL")
        # Get access to the question bank
        self.question_bank = get_question_bank()
        # Track used questions in this session
        self._used_question_ids: Set[str] = set()
        # Set up logger
        self.logger = logging.getLogger(
            "ai.agent.gemini"
        )  # Register available tools for function calling

    def get_next_question(
        self,
        capabilities: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve the next question from the local bank.

        This function automatically avoids repeating questions within the current session.

        Args:
            capabilities: Optional list of capabilities to target (e.g., ["Formulas", "Pivot Tables"]).
            difficulty: Optional difficulty filter (e.g., "Easy", "Medium", "Hard", "Advanced").

        Returns:
            A dictionary with keys: id (str), text (str), difficulty (str), capabilities (List[str]).
        """
        # Log tool call for submission visibility
        self.logger.warning(
            "🔧 TOOL CALL: get_next_question | capabilities=%s | difficulty=%s",
            capabilities,
            difficulty,
        )

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

        result = {
            "id": question.id,
            "text": question.text,
            "difficulty": question.difficulty,
            "capabilities": question.capabilities,
        }

        # Log successful question retrieval
        self.logger.warning(
            "✅ QUESTION RETRIEVED | id=%s | difficulty=%s | capabilities=%s",
            question.id,
            question.difficulty,
            question.capabilities,
        )

        return result

    def generate_reply(
        self, messages: List[Message], state: Optional[Dict[str, Any]] = None
    ) -> AIResponseWrapped:
        """Generate a response using Gemini AI.

        This method signature MUST match the AIAgent Protocol exactly.
        The Protocol ensures type safety and interface consistency.
        """

        # Convert messages to Gemini format
        gemini_messages = self._convert_messages_to_gemini_format(messages)

        # Build the system prompt based on interview context
        system_prompt = self._build_system_prompt(state)

        # Prepare the full prompt
        full_prompt = f"{system_prompt}\n\nConversation:\n" + "\n".join(gemini_messages)

        # Log LLM request details to file only
        self.logger.debug(
            "LLM_REQUEST | message_count=%d | prompt_length=%d",
            len(messages),
            len(full_prompt),
        )

        try:
            # Call Gemini API with function-calling tools (no structured outputs)
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    tools=[self.get_next_question, self.generate_question]
                ),
            )

            # Log basic API response info (detailed response goes to file only)
            self.logger.debug(
                "LLM_RAW_RESPONSE | text_length=%d", len(getattr(response, "text", ""))
            )

            # Extract response text
            reply_text_raw: str = getattr(response, "text", "").strip()

            # Parse flags from the response tail and clean them from user-visible text
            cleaned_text, end_flag, question_id_from_flags = (
                parse_response_flags_and_clean_text(reply_text_raw)
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
                    "agent": "gemini",
                    "model": self.model,
                    "tokens_used": getattr(response, "usage", {}).get(
                        "total_tokens", 0
                    ),
                    "questions_used": len(self._used_question_ids),
                    "question_id": question_id_from_flags,
                },
                end=should_end,
            )

            # Log essential response info
            self.logger.info(
                "LLM_RESPONSE | end=%s | tokens_used=%s | questions_used=%d",
                should_end,
                wrapped_response.metadata.get("tokens_used", 0),
                wrapped_response.metadata.get("questions_used", 0),
            )

            return wrapped_response

        except Exception as e:
            # Log the error details
            self.logger.error(
                "LLM_ERROR | %s | message_count=%d", str(e), len(messages)
            )

            # Fallback response if Gemini fails
            return AIResponseWrapped(
                text=f"I apologize, but I'm having trouble connecting to Gemini right now. Error: {str(e)}",
                metadata={
                    "agent": "gemini",
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

        question_count = self.question_bank.get_question_count()
        available_capabilities = self.question_bank.get_available_capabilities()
        available_difficulties = self.question_bank.get_available_difficulties()
        session_id = state.get("session_id") if state else None

        return render_system_prompt(
            question_count=question_count,
            available_capabilities=available_capabilities,
            available_difficulties=available_difficulties,
            session_id=session_id,
        )

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
        return self.question_bank.select_random_question(
            exclude_ids=self._used_question_ids,
            capabilities=capabilities,
            difficulty=difficulty,
        )

    def generate_question(
        self,
        capabilities: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        additional_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a brand-new Excel interview question via LLM and save it.

        Args:
            capabilities: Optional list of target capabilities (e.g., ["Formulas", "Pivot Tables"]).
            difficulty: Optional difficulty filter (e.g., "Easy", "Medium", "Hard", "Advanced").
            additional_notes: Optional brief guidance on what to emphasize.

        Returns:
            A dictionary with keys: id (str), text (str), difficulty (str), capabilities (List[str]).
        """
        # Log tool call for submission visibility
        self.logger.warning(
            "🔧 TOOL CALL: generate_question | capabilities=%s | difficulty=%s | notes=%s",
            capabilities,
            difficulty,
            additional_notes,
        )

        try:
            # Compose generation prompt and call LLM separately
            gen_payload = self._generate_question_via_llm(
                capabilities=capabilities,
                difficulty=difficulty,
                additional_notes=additional_notes,
            )

            # Normalize fields
            text_raw = str(gen_payload.get("text", "")).strip()
            if not text_raw:
                raise ValueError("Generated question text is empty")

            gen_caps = gen_payload.get("capabilities", capabilities or [])
            if isinstance(gen_caps, str):
                # Split on comma/pipe
                gen_caps = [c.strip() for c in re.split(r",|\|", gen_caps) if c.strip()]
            if not isinstance(gen_caps, list):
                gen_caps = list(gen_caps)  # best-effort
            gen_caps = [str(c).strip() for c in gen_caps if str(c).strip()]

            gen_diff = str(
                gen_payload.get("difficulty") or (difficulty or "Medium")
            ).strip()
            eval_criteria = gen_payload.get("evaluation_criteria") or []
            if isinstance(eval_criteria, str):
                # Split string into list if needed
                eval_criteria = [
                    s.strip() for s in re.split(r"\n|,|\|", eval_criteria) if s.strip()
                ]
            if not isinstance(eval_criteria, list):
                eval_criteria = list(eval_criteria)
            eval_criteria = [str(e).strip() for e in eval_criteria if str(e).strip()]

            # Persist to the question bank and get the new id
            new_id = (
                self.question_bank.add_question_and_get_id(
                    text=text_raw,
                    capabilities=gen_caps,
                    difficulty=gen_diff,
                    question_id=None,
                    evaluation_criteria=eval_criteria,
                )
                or ""
            )

            if new_id:
                self._used_question_ids.add(new_id)

            result = {
                "id": new_id,
                "text": text_raw,
                "difficulty": gen_diff,
                "capabilities": gen_caps,
            }

            # Log successful question generation
            self.logger.warning(
                "✅ QUESTION GENERATED | id=%s | difficulty=%s | capabilities=%s",
                new_id,
                gen_diff,
                gen_caps,
            )

            return result

        except Exception as e:
            self.logger.error("GENERATE_QUESTION_ERROR | %s", str(e))
            return {
                "id": "",
                "text": "Unable to generate a new question at this time.",
                "difficulty": difficulty or "",
                "capabilities": capabilities or [],
            }

    def _generate_question_via_llm(
        self,
        capabilities: Optional[List[str]],
        difficulty: Optional[str],
        additional_notes: Optional[str],
    ) -> Dict[str, Any]:
        """Call the LLM to produce a new question JSON with evaluation criteria."""
        instruction = render_generate_question_prompt(
            capabilities=capabilities,
            difficulty=difficulty,
            additional_notes=additional_notes,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=instruction,
            config=types.GenerateContentConfig(),
        )

        raw_text = getattr(response, "text", "").strip()

        # Strip code fences if present
        cleaned = raw_text
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`\n ")
            # If there is a language tag, drop the first line
            if "\n" in cleaned:
                first_line, rest = cleaned.split("\n", 1)
                if not first_line.strip().startswith("{"):
                    cleaned = rest.strip()

        # Attempt to extract JSON substring
        json_str = cleaned
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = json_str[start : end + 1]

        try:
            payload = json.loads(json_str)
            if not isinstance(payload, dict):
                raise ValueError("Non-object JSON returned")
            return payload
        except Exception as parse_err:
            self.logger.error("PARSE_GENERATE_QUESTION_JSON_ERROR | %s", str(parse_err))
            # Best-effort fallback: wrap as minimal payload
            return {
                "text": cleaned if cleaned else "",
                "capabilities": capabilities or [],
                "difficulty": difficulty or "Medium",
                "evaluation_criteria": [],
            }

    def generate_performance_summary(self, messages: List[Message]) -> str:
        """Generate a detailed performance summary based on the interview transcript.

        Args:
            messages: List of Message objects from the interview transcript

        Returns:
            A detailed performance evaluation summary as a string
        """
        try:
            # Extract only the relevant conversation content (no metadata)
            transcript_content = self._extract_transcript_content(messages)

            # Build the evaluation prompt
            evaluation_prompt = render_performance_evaluation_prompt(transcript_content)

            # Log the evaluation request for submission visibility
            self.logger.warning(
                "🔧 TOOL CALL: generate_performance_summary | message_count=%d",
                len(messages),
            )

            # Call Gemini API for evaluation
            response = self.client.models.generate_content(
                model=self.model,
                contents=evaluation_prompt,
                config=types.GenerateContentConfig(),
            )

            # Extract the evaluation text
            evaluation_text = getattr(response, "text", "").strip()

            # Log successful evaluation for submission visibility
            self.logger.warning(
                "✅ PERFORMANCE SUMMARY GENERATED | length=%d", len(evaluation_text)
            )

            return evaluation_text

        except Exception as e:
            # Log the error
            self.logger.error(
                "PERFORMANCE_EVALUATION_ERROR | %s | message_count=%d",
                str(e),
                len(messages),
            )

            # Return a fallback summary
            return (
                "## Performance Evaluation\n\n"
                "We apologize, but we were unable to generate a detailed performance summary at this time due to a technical issue. "
                "Please review the interview transcript manually for assessment.\n\n"
                f"Error: {str(e)}"
            )

    def _extract_transcript_content(self, messages: List[Message]) -> str:
        """Extract only the relevant conversation content from messages, excluding metadata."""
        conversation_lines = []

        for msg in messages:
            # Skip system messages
            if msg.role == "system":
                continue

            # Format as simple conversation
            role_display = "Interviewer" if msg.role == "assistant" else "Candidate"
            conversation_lines.append(f"{role_display}: {msg.content}")

        return "\n\n".join(conversation_lines)


def get_agent() -> AIAgent:
    """Factory function that returns the Gemini agent.

    This function signature is part of the Protocol contract.
    The Protocol ensures that whatever this returns implements
    the AIAgent interface.
    """
    return GeminiAgent()
