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
    various criteria like difficulty, capabilities, or randomly.
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
                    capabilities=item.get("capabilities", ""),
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
            if capability_lower in [c.lower() for c in q.capabilities]
        ]

    def get_questions_by_capabilities(self, capabilities: List[str]) -> List[Question]:
        """Get questions that match any of the provided capabilities."""
        capabilities_lower = [c.lower() for c in capabilities]
        return [
            q
            for q in self._questions
            if any(
                cap_lower in [c.lower() for c in q.capabilities]
                for cap_lower in capabilities_lower
            )
        ]

    def select_random_question(
        self,
        exclude_ids: Optional[Set[str]] = None,
        difficulty: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> Optional[Question]:
        """Select a random question based on optional filters.

        Args:
            exclude_ids: Set of question IDs to exclude from selection
            difficulty: Filter by difficulty level
            capabilities: Filter by capabilities

        Returns:
            A randomly selected Question or None if no questions match criteria
        """
        candidates = self._questions

        # Apply filters
        if exclude_ids:
            candidates = [q for q in candidates if q.id not in exclude_ids]

        if difficulty:
            candidates = self.get_questions_by_difficulty(difficulty)

        if capabilities:
            capabilities_lower = [c.lower() for c in capabilities]
            candidates = [
                q
                for q in candidates
                if any(
                    cap_lower in [c.lower() for c in q.capabilities]
                    for cap_lower in capabilities_lower
                )
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
            capabilities.update(question.capabilities)
        return sorted(list(capabilities))

    def get_available_difficulties(self) -> List[str]:
        """Get all unique difficulty levels in the question bank."""
        difficulties = set()
        for question in self._questions:
            difficulties.add(question.difficulty)
        return sorted(list(difficulties))

    def _generate_unique_id(self) -> str:
        """Generate a unique ID for a new question."""
        if not self._questions:
            return "1"

        # Find the maximum numeric ID and increment by 1
        max_id = 0
        for question in self._questions:
            try:
                max_id = max(max_id, int(question.id))
            except ValueError:
                # If ID is not numeric, skip it
                continue

        return str(max_id + 1)

    def _save_questions_to_file(self) -> bool:
        """Save all questions to the JSON file.

        Returns:
            True if save was successful, False otherwise
        """
        try:
            path = Path(self._question_bank_path)
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Convert questions to dictionaries for JSON serialization
            questions_data = []
            for question in self._questions:
                questions_data.append(
                    {
                        "id": question.id,
                        "capabilities": question.capabilities,
                        "difficulty": question.difficulty,
                        "text": question.text,
                    }
                )

            with open(path, "w", encoding="utf-8") as f:
                json.dump(questions_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving question bank: {e}")
            return False

    def add_question(
        self,
        text: str,
        capabilities: List[str],
        difficulty: str,
        question_id: Optional[str] = None,
    ) -> bool:
        """Add a new question to the question bank.

        Args:
            text: The question text
            capabilities: List of capabilities this question tests
            difficulty: Difficulty level (e.g., "Easy", "Medium", "Hard", "Advanced")
            question_id: Optional custom ID. If not provided, generates a unique ID.

        Returns:
            True if question was added successfully, False otherwise
        """
        # Validate inputs
        if not text.strip():
            print("Error: Question text cannot be empty")
            return False

        if not capabilities:
            print("Error: At least one capability must be specified")
            return False

        if not difficulty.strip():
            print("Error: Difficulty cannot be empty")
            return False

        for cap in capabilities:
            if not isinstance(cap, str) or not cap.strip():
                print("Error: All capabilities must be non-empty strings")
                return False

        # Generate ID if not provided
        if question_id is None:
            question_id = self._generate_unique_id()
        elif not question_id.strip():
            print("Error: Question ID cannot be empty")
            return False

        # Check if ID already exists
        existing_ids = {q.id for q in self._questions}
        if question_id in existing_ids:
            print(f"Error: Question ID '{question_id}' already exists")
            return False

        # Create new question
        try:
            new_question = Question(
                id=question_id,
                capabilities=[cap.strip() for cap in capabilities],  # Clean whitespace
                difficulty=difficulty.strip(),
                text=text.strip(),
            )

            # Add to in-memory collection
            self._questions.append(new_question)

            # Save to file
            if not self._save_questions_to_file():
                # If save failed, remove from memory
                self._questions.pop()
                return False

            return True

        except Exception as e:
            print(f"Error creating question: {e}")
            return False


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


def add_question_to_bank(
    text: str,
    capabilities: List[str],
    difficulty: str,
    question_id: Optional[str] = None,
) -> bool:
    """Add a new question to the global question bank instance.

    Args:
        text: The question text
        capabilities: List of capabilities this question tests
        difficulty: Difficulty level (e.g., "Easy", "Medium", "Hard", "Advanced")
        question_id: Optional custom ID. If not provided, generates a unique ID.

    Returns:
        True if question was added successfully, False otherwise
    """
    question_bank = get_question_bank()
    return question_bank.add_question(text, capabilities, difficulty, question_id)
