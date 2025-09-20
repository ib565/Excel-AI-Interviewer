from __future__ import annotations

from typing import List, Optional


def render_system_prompt(
    question_count: int,
    available_capabilities: List[str],
    available_difficulties: List[str],
    session_id: Optional[str] = None,
) -> str:
    """Render the system prompt given question bank context and optional session id."""

    lines: List[str] = [
        "You are an expert Excel interviewer conducting a mock interview.",
        "Your goal is to assess the candidate's Excel skills through conversation.",
        "",
        "Guidelines:",
        "- Ask specific, technical Excel questions using the available tool when needed.",
        "- Follow up on their answers with clarifying questions.",
        "- Be conversational but professional.",
        "- End the interview after max 5 questions or when appropriate. Your last message should be a comprehensive summary of the interview with the flag [[END=true QID=none]]",
        "",
        "Tool-use contract:",
        "- When you need a new question from the bank, CALL get_next_question(capabilities?, difficulty?).",
        "- If the bank has no suitable question (i.e., the tool returns an empty id or the text 'No more suitable questions are available.'), then make ANOTHER TOOL CALL to generate_question(capabilities?, difficulty?, additional_notes?).",
        "  Provide 'additional_notes' as a short phrase that to guide the question generation).",
        "- After composing your reply for the candidate, append a single flags line EXACTLY in this form:",
        "  [[END=<true|false> QID=<question_id or none>]]",
        "- Do not include the flags in the visible body of your message; put them only at the very end.",
        "",
    ]

    if question_count > 0:
        lines.extend(
            [
                f"Available questions: {question_count}",
                f"Capabilities: {', '.join(sorted(set(available_capabilities)))}",
                f"Difficulty levels: {', '.join(sorted(set(available_difficulties)))}",
                "",
                "Selection guidance:",
                "- Start with easier questions and progress to harder ones.",
                "- Choose questions that build on the candidate's previous answers.",
                "- Avoid repeating questions within the same interview.",
            ]
        )

    if session_id:
        lines.append(f"\n- Session ID: {session_id}")

    return "\n".join(lines)


def render_generate_question_prompt(
    capabilities: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
    additional_notes: Optional[str] = None,
) -> str:
    """Render the instruction for generating a new Excel interview question."""

    caps_str = ", ".join(capabilities or [])
    diff = difficulty or "Medium"
    notes = (additional_notes or "").strip() or "none"

    lines: List[str] = [
        "You are generating a single, clear Excel interview question.",
        "Requirements:",
        f"- Target capabilities: {caps_str if caps_str else '(use sensible Excel capability)'}",
        f"- Difficulty: {diff}",
        f"- Additional notes: {notes}",
        "",
        "Output STRICTLY a compact JSON object with keys:",
        "  text (string), capabilities (array of strings), difficulty (string), evaluation_criteria (array of strings).",
        "- Do not include markdown fences or commentary.",
        "- The question should be answerable conversationally and focused on Excel.",
        "- The question should be general and reusable for multiple candidates.",
        "- Provide 3-6 evaluation_criteria that are specific and observable.",
    ]

    return "\n".join(lines)


__all__ = [
    "render_system_prompt",
    "render_generate_question_prompt",
]
