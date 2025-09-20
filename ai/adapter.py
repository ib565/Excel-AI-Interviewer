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
        self.model = os.getenv("MODEL")
        # Get access to the question bank
        self.question_bank = get_question_bank()
        # Track used questions in this session
        self._used_question_ids: Set[str] = set()
        # Set up logger
        self.logger = logging.getLogger(
            "ai.adapter.gemini"
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
                config=types.GenerateContentConfig(
                    tools=[self.get_next_question, self.generate_question]
                ),
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
            "- End the interview after max 5 questions or when appropriate. Your last message should be a comprehensive summary of the interview with the flag [[END=true QID=none]]\n\n"
            "Tool-use contract:\n"
            "- When you need a new question from the bank, CALL get_next_question(capabilities?, difficulty?).\n"
            "- If the bank has no suitable question (i.e., the tool returns an empty id or the text 'No more suitable questions are available.'), then make ANOTHER TOOL CALL to generate_question(capabilities?, difficulty?, additional_notes?).\n"
            "  Provide 'additional_notes' as a short phrase that to guide the question generation).\n"
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

            # Persist to the question bank with a predicted new id
            new_id = self._compute_next_question_id()
            saved = self.question_bank.add_question(
                text=text_raw,
                capabilities=gen_caps,
                difficulty=gen_diff,
                question_id=new_id,
                evaluation_criteria=eval_criteria,
            )

            if not saved:
                # Attempt once more with auto-id
                fallback_save = self.question_bank.add_question(
                    text=text_raw,
                    capabilities=gen_caps,
                    difficulty=gen_diff,
                    question_id=None,
                    evaluation_criteria=eval_criteria,
                )
                if fallback_save:
                    # Best effort to determine id: use max numeric id
                    new_id = self._compute_highest_numeric_id()
                else:
                    # As a last resort, return a non-persistent question
                    new_id = ""

            if new_id:
                self._used_question_ids.add(new_id)

            return {
                "id": new_id,
                "text": text_raw,
                "difficulty": gen_diff,
                "capabilities": gen_caps,
            }

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
        caps_str = ", ".join(capabilities or [])
        notes = additional_notes.strip() if additional_notes else ""
        diff = difficulty or "Medium"

        instruction = (
            "You are generating a single, clear Excel interview question.\n"
            "Requirements:\n"
            "- Target capabilities: "
            + (caps_str if caps_str else "(use sensible Excel capability)")
            + "\n"
            "- Difficulty: " + diff + "\n"
            "- Additional notes: " + (notes if notes else "none") + "\n\n"
            "Output STRICTLY a compact JSON object with keys: \n"
            "  text (string), capabilities (array of strings), difficulty (string), evaluation_criteria (array of strings).\n"
            "- Do not include markdown fences or commentary.\n"
            "- The question should be answerable conversationally and focused on Excel.\n"
            "- The question should be general and reusable for multiple candidates."
            "- Provide 3-6 evaluation_criteria that are specific and observable.\n"
        )

        self.logger.debug("LLM_REQUEST_GENERATE_QUESTION | %s", instruction)
        response = self.client.models.generate_content(
            model=self.model,
            contents=instruction,
            config=types.GenerateContentConfig(),
        )

        raw_text = getattr(response, "text", "").strip()
        self.logger.debug("LLM_RAW_RESPONSE_GENERATE_QUESTION | %s", raw_text)

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
                "difficulty": diff,
                "evaluation_criteria": [],
            }

    def _compute_next_question_id(self) -> str:
        """Compute the next numeric question id based on current bank."""
        ids: List[int] = []
        for q in self.question_bank.get_all_questions():
            try:
                ids.append(int(q.id))
            except Exception:
                continue
        next_id = (max(ids) + 1) if ids else 1
        return str(next_id)

    def _compute_highest_numeric_id(self) -> str:
        ids: List[int] = []
        for q in self.question_bank.get_all_questions():
            try:
                ids.append(int(q.id))
            except Exception:
                continue
        return str(max(ids) if ids else 0)

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
