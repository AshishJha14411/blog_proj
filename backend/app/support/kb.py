"""
/** WHY: Phase 4 grounding v1. The chatbot needs one source of truth for
    product facts (roles, moderation flow, common flows). Pointing the LLM
    at kb.md via the system prompt is the simplest useful grounding — real
    vector RAG is a later, separate project. **/

/** WHAT: `get_kb_text()` returns the KB content, cached at process start
    so we don't re-read the file on every message. **/
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_KB_PATH = Path(__file__).with_name("kb.md")


@lru_cache(maxsize=1)
def get_kb_text() -> str:
    """
    /** WHAT: read the KB file and cache it. If the file is missing we
        return an empty string — the bot still works, just without
        grounding. Loud logging on that case would be a good follow-up. **/
    """
    try:
        return _KB_PATH.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""
