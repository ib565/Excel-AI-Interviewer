Excel Interviewer AI (PoC)

A minimal Streamlit app scaffold where an external AI module (Gemini later) will drive the interview logic. Ships with a built-in local stub so you can test end-to-end.

What works now
- Enter self-assessment and start a session
- Send a chat message
- Receive a canned assistant reply (local stub)
- Transcript saved as JSONL per session under `transcripts/`
- Log file per session under `logs/`
- Download transcript

Structure
- `app/` Streamlit UI
- `core/` Pydantic models and AI adapter bridge
- `storage/` Transcript helpers (JSONL)
- `data/` Tiny sample question bank (optional)
- `config.py` Paths and setup helpers

Run locally (Windows PowerShell)
1. Ensure your venv is activated
2. Install deps and run Streamlit:
```
cd "C:\Users\ishui\Desktop\2ExcelInterviewerAI"
.\venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install streamlit pydantic python-dotenv
streamlit run app\\main.py
```

Plug in your AI later
Create `ai/adapter.py` with a `get_adapter()` that returns an object implementing:
```
def generate_reply(messages: list[Message], state: dict | None = None) -> AIResponse
```
If `ai.adapter` is missing, the app uses a built-in local echo stub.

Transcript format (JSONL)
Each line is a JSON object with `type: "message"` or `type: "event"`.
```
{"type":"message","session_id":"...","timestamp":"...","role":"user","content":"hi"}
{"type":"message","session_id":"...","timestamp":"...","role":"assistant","content":"Stub reply...","metadata":{"adapter":"local_echo_stub"}}
{"type":"event","session_id":"...","timestamp":"...","event":"end"}
```

Notes
- No rule-based selection or scoring in the app. The AI will decide later.
- The question bank is optional and passed to the AI via `state`.


