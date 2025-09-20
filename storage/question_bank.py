from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config import QUESTION_BANK_PATH
from core.models import Question


class QuestionBank:
    """Service for managing and selecting questions from the question bank.

    This class provides methods to load questions and select them based on
    various criteria like difficulty, capability, or randomly.
    """

    def __init__(self, question_bank_path: Optional[str] = None):
        """Initialize the QuestionBank service.

        Args:
            question_bank_path: Path to question bank JSON file.
                               If None, uses config.QUESTION_BANK_PATH
        """
        self._question_bank_path = question_bank_path or QUESTION_BANK_PATH
        self._questions: List[Question] = []
        self._load_questions()

    def _load_questions(self) -> None:
        """Load questions from the JSON file."""
        path = Path(self._question_bank_path)
        if not path.exists():
            self._questions = []
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._questions = []
            for item in data:
                question = Question(
                    id=str(item.get("id", "")),
                    capability=item.get("capability", ""),
                    difficulty=item.get("difficulty", ""),
                    text=item.get("text", ""),
                )
                self._questions.append(question)

        except Exception as e:
            print(f"Error loading question bank: {e}")
            self._questions = []

    def get_all_questions(self) -> List[Question]:
        """Return all questions."""
        return self._questions.copy()

    def get_question_count(self) -> int:
        """Return the total number of questions."""
        return len(self._questions)

    def get_questions_by_difficulty(self, difficulty: str) -> List[Question]:
        """Get questions filtered by difficulty level."""
        return [
            q for q in self._questions if q.difficulty.lower() == difficulty.lower()
        ]

    def get_questions_by_capability(self, capability: str) -> List[Question]:
        """Get questions filtered by capability."""
        capability_lower = capability.lower()
        return [
            q
            for q in self._questions
            if capability_lower in [c.lower() for c in q.capability]
        ]

    def get_questions_by_capabilities(self, capabilities: List[str]) -> List[Question]:
        """Get questions that match any of the provided capabilities."""
        capabilities_lower = [c.lower() for c in capabilities]
        return [
            q
            for q in self._questions
            if any(
                cap_lower in [c.lower() for c in q.capability]
                for cap_lower in capabilities_lower
            )
        ]

    def select_random_question(
        self,
        exclude_ids: Optional[Set[str]] = None,
        difficulty: Optional[str] = None,
        capability: Optional[str] = None,
    ) -> Optional[Question]:
        """Select a random question based on optional filters.

        Args:
            exclude_ids: Set of question IDs to exclude from selection
            difficulty: Filter by difficulty level
            capability: Filter by capability

        Returns:
            A randomly selected Question or None if no questions match criteria
        """
        candidates = self._questions

        # Apply filters
        if exclude_ids:
            candidates = [q for q in candidates if q.id not in exclude_ids]

        if difficulty:
            candidates = self.get_questions_by_difficulty(difficulty)

        if capability:
            candidates = [
                q
                for q in candidates
                if capability.lower() in [c.lower() for c in q.capability]
            ]

        if not candidates:
            return None

        return random.choice(candidates)

    def select_questions(
        self,
        count: int,
        exclude_ids: Optional[Set[str]] = None,
        difficulty: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> List[Question]:
        """Select multiple questions based on criteria.

        Args:
            count: Number of questions to select
            exclude_ids: Set of question IDs to exclude
            difficulty: Filter by difficulty level
            capabilities: Filter by capabilities (questions matching any capability)

        Returns:
            List of selected questions
        """
        candidates = self._questions

        # Apply filters
        if exclude_ids:
            candidates = [q for q in candidates if q.id not in exclude_ids]

        if difficulty:
            candidates = self.get_questions_by_difficulty(difficulty)

        if capabilities:
            candidates = self.get_questions_by_capabilities(capabilities)

        # Randomly sample without replacement
        available_count = len(candidates)
        if available_count <= count:
            return candidates.copy()

        return random.sample(candidates, count)

    def get_available_capabilities(self) -> List[str]:
        """Get all unique capabilities in the question bank."""
        capabilities = set()
        for question in self._questions:
            capabilities.update(question.capability)
        return sorted(list(capabilities))

    def get_available_difficulties(self) -> List[str]:
        """Get all unique difficulty levels in the question bank."""
        difficulties = set()
        for question in self._questions:
            difficulties.add(question.difficulty)
        return sorted(list(difficulties))


# Global instance for easy access
_question_bank_instance: Optional[QuestionBank] = None


def get_question_bank() -> QuestionBank:
    """Get or create the global QuestionBank instance."""
    global _question_bank_instance
    if _question_bank_instance is None:
        _question_bank_instance = QuestionBank()
    return _question_bank_instance


def reload_question_bank() -> QuestionBank:
    """Force reload the question bank from disk."""
    global _question_bank_instance
    _question_bank_instance = QuestionBank()
    return _question_bank_instance
