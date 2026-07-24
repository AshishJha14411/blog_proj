"""
/** WHY: chat session store is what keeps a conversation continuous across
    reconnects, and the budget guardrail is the only thing between us and
    a runaway LLM bill. Both need to be correct. **/
"""
from __future__ import annotations

from unittest.mock import MagicMock

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import redis as redis_module
from app.support import session as chat_session


def test_append_and_get_history_roundtrips():
    """Messages appear in insertion order, oldest first."""
    chat_session.append_message("s1", "user", "hello")
    chat_session.append_message("s1", "assistant", "hi there")
    chat_session.append_message("s1", "user", "how are you?")

    hist = chat_session.get_history("s1")
    contents = [m["content"] for m in hist]
    assert contents == ["hello", "hi there", "how are you?"]


def test_history_is_bounded_to_max():
    """After MAX_HISTORY messages, older ones are trimmed off the front."""
    for i in range(chat_session.MAX_HISTORY + 5):
        chat_session.append_message("s2", "user", f"m{i}")
    hist = chat_session.get_history("s2")
    assert len(hist) == chat_session.MAX_HISTORY
    # Oldest survivors are the 5th and later (m5, m6, …)
    assert hist[0]["content"] == "m5"


def test_get_history_empty_by_default():
    assert chat_session.get_history("no-such-session") == []


def test_budget_allows_up_to_cap():
    """First DAILY_MESSAGE_BUDGET calls return True; the next one is False."""
    uid = "user-a"
    for _ in range(chat_session.DAILY_MESSAGE_BUDGET):
        assert chat_session.claim_budget(uid) is True
    # One over the cap must be refused.
    assert chat_session.claim_budget(uid) is False


def test_budget_is_per_user():
    uid_a = "user-x"
    uid_b = "user-y"
    for _ in range(chat_session.DAILY_MESSAGE_BUDGET):
        chat_session.claim_budget(uid_a)
    # User A is now blocked; user B is still fresh.
    assert chat_session.claim_budget(uid_a) is False
    assert chat_session.claim_budget(uid_b) is True


def test_budget_fails_open_on_redis_error(monkeypatch):
    """Redis outage must not lock everyone out of chat — soft policy."""
    boom = MagicMock()
    boom.pipeline.side_effect = RedisConnectionError("down")
    monkeypatch.setattr(redis_module, "get_redis_client", lambda: boom)

    assert chat_session.claim_budget("user-z") is True
