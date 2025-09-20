from __future__ import annotations

from typing import List, Optional


def render_system_prompt(
    question_count: int,
    available_capabilities: List[str],
    available_difficulties: List[str],
    session_id: Optional[str] = None,
) -> str:
    """Render the system prompt given question bank context and optional session id."""

    base_prompt = """You are an expert Excel interviewer conducting a quick interview.
Your goal is to assess the candidate's Excel skills through conversation.

Guidelines:
- Ask specific, technical Excel questions using the available tool when needed.
- Follow up on their answers with clarifying questions.
- Keep the interview short.
- Be conversational but professional.
- Challenge the candidate by stepping up the difficulty if they are comfortable with the current question.
- End the interview after max 3 questions or when appropriate. Your last message should have the flag [[END=true QID=none]]. Do not give any feedback or summary.

Tool-use contract:
- When you need a new question from the bank, CALL get_next_question(capabilities?, difficulty?).
- If the bank has no suitable question (i.e., the tool returns an empty id or the text 'No more suitable questions are available.'), then make ANOTHER TOOL CALL to generate_question(capabilities?, difficulty?, additional_notes?).
  Provide 'additional_notes' as a short phrase that to guide the question generation).
- After composing your reply for the candidate, append a single flags line EXACTLY in this form:
  [[END=<true|false> QID=<question_id or none>]]
- Do not include the flags in the visible body of your message; put them only at the very end.
"""

    if question_count > 0:
        base_prompt += f"""
Available questions: {question_count}
Capabilities: {', '.join(sorted(set(available_capabilities)))}
Difficulty levels: {', '.join(sorted(set(available_difficulties)))}

Selection guidance:
- Start with easier questions and progress to harder ones.
- Choose questions that build on the candidate's previous answers.
- Avoid repeating questions within the same interview.
"""

    if session_id:
        base_prompt += f"\n- Session ID: {session_id}"

    return base_prompt


def render_generate_question_prompt(
    capabilities: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
    additional_notes: Optional[str] = None,
) -> str:
    """Render the instruction for generating a new Excel interview question."""

    caps_str = ", ".join(capabilities or [])
    diff = difficulty or "Medium"
    notes = (additional_notes or "").strip() or "none"

    return f"""You are generating a single, clear Excel interview question.
Requirements:
- Target capabilities: {caps_str if caps_str else '(use sensible Excel capability)'}
- Difficulty: {diff}
- Additional notes: {notes}

Output STRICTLY a compact JSON object with keys:
  text (string), capabilities (array of strings), difficulty (string), evaluation_criteria (array of strings).
- Do not include markdown fences or commentary.
- The question should be answerable conversationally and focused on Excel.
- The question should be general and reusable for multiple candidates.
- Provide 3-6 evaluation_criteria that are specific and observable."""


def render_performance_evaluation_prompt(transcript_content: str) -> str:
    """Render the prompt for evaluating candidate performance from interview transcript."""

    return f"""You are an expert Excel interviewer evaluating a candidate's performance based on their interview transcript.

Your task is to provide a detailed, constructive performance summary that includes:

1. **Overall Assessment**: Rate their Excel proficiency level (Beginner, Intermediate, Advanced, Expert)
2. **Strengths**: Specific areas where they demonstrated strong Excel knowledge or skills
3. **Areas for Improvement**: Topics or skills that need development
4. **Technical Accuracy**: How well they answered technical questions
5. **Communication Skills**: Clarity and effectiveness of their explanations
6. **Problem-Solving Approach**: How they approached Excel-related challenges

Guidelines:
- Be constructive and encouraging while being honest about weaknesses
- Base your evaluation only on the content of the transcript provided
- Focus on Excel-specific skills and concepts demonstrated
- Provide specific examples from the conversation to support your assessment
- Keep the summary comprehensive but concise (aim for 400-600 words)
- Use clear, professional language suitable for HR or technical reviewers
- DO NOT include any header templates like "Candidate: [Name]" or "Evaluator: [Name]" - focus only on the evaluation content

INTERVIEW TRANSCRIPT:
{transcript_content}

Please provide your evaluation in a well-structured format with clear sections and bullet points where appropriate."""


__all__ = [
    "render_system_prompt",
    "render_generate_question_prompt",
    "render_performance_evaluation_prompt",
]
