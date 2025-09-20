Excel Interviewer — AI‑first Mock Interviewer (PoC)


A conversational, LLM‑driven mock interviewer that assesses Excel skills.

Designed as a lightweight PoC: Streamlit front end + Python orchestration, with Gemini (or another structured LLM) handling question generation, evaluation, and conversational behavior.

Quick summary


- LLM‑first: the model drives conversation, personalizes questions, and grades

answers using structured outputs.

- Retrieval‑first: pick questions from a small bank; fall back to controlled

generation if no match.

- Conversational: starts with a self‑assessment, adapts difficulty, asks clarifying

follow‑ups when grading confidence is low, then summarizes performance.

- PoC scope: no full Excel engine — formula answers are judged by LLM rubric +

mental checks. Transcripts saved locally.

Why this approach


- Fast to build and iterate (Streamlit).

- Human‑like interview experience driven by the LLM.

- Controlled generation + validation for stability.

- Structured outputs and Gemini function calling ensure predictable

machine‑readable results (scores, follow‑ups, next action).

Core features


- Self‑assessment kickoff that guides personalization.

- Retrieve‑from‑bank (preferred) then generate question fallback.

- LLM evaluation returning structured JSON: per‑criterion scores,

total (0–5), confidence and short advice.

- Follow‑up probing when confidence is low or score is borderline.

- Session transcript + final summary (per‑capability subscores and tips).

- Cap on generated questions per interview (e.g., ≤ 2) for stability.

Tech stack


- Python

- Streamlit (UI + orchestration)

- Pydantic for schemas (Question, AnswerSpec, Evaluation, AssistantMessage)

- Gemini (or equivalent) for LLM with function calling / structured outputs

- Local JSON/JSONL for bank and transcript storage