from __future__ import annotations

import re
from typing import Optional, Tuple


def parse_response_flags_and_clean_text(text: str) -> Tuple[str, bool, Optional[str]]:
    """Extract end/QID flags from the response tail and return cleaned text.

    Expected trailing token format: [[END=true QID=123]]
    Returns (cleaned_text, end_flag, question_id)
    """
    if not text:
        return "", False, None

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

    cleaned = text[: match.start()].rstrip()
    return cleaned, end_flag, question_id
