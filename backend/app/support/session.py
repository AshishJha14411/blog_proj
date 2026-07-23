"""
/** WHY: chat sessions need persistence across (a) reconnects and (b) the
    stateless request layer. Redis lists are a natural fit — O(1) append
    at the tail, O(1) trim to keep the last N. **/

/** WHAT:
      - append_message(session_id, role, content) — LPUSH then LTRIM to cap.
      - get_history(session_id)                    — LRANGE, oldest first.
      - claim_budget(user_id)                      — INCR under a per-day
                                                     key with an EXPIREAT
                                                     to midnight UTC.
      Returns False if the daily cap is exhausted. **/

/** WHY-THIS-WAY:
    - LPUSH+LTRIM preserves the last N messages without ever touching a
      SORT operation. The list acts as a bounded ring.
    - Per-day budget by INCR-then-check: single round-trip, race-free. **/
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Literal, TypedDict

from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# recommended by claude opus 4.7: cap sessions at 30 messages. Enough to
# preserve conversational context (Q → A → follow-up × 15) but bounded so
# system prompts stay cheap.
MAX_HISTORY = 30

# 24h session TTL — long enough that a user closing the tab and coming
# back the next morning still sees the conversation.
SESSION_TTL_SECONDS = 60 * 60 * 24

# Daily message budget. LLM tokens are money — cap them per user.
DAILY_MESSAGE_BUDGET = 50


ChatRole = Literal["user", "assistant", "system"]


class ChatMessage(TypedDict):
    role: ChatRole
    content: str
    ts: str  # ISO timestamp, useful for the frontend to render timestamps


def _session_key(session_id: str) -> str:
    return f"chat:{session_id}"


def _budget_key(user_id: str) -> str:
    # recommended by claude opus 4.7: bucket by UTC day so the reset moment
    # is deterministic. Local-time buckets create surprising DST windows.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"chat_budget:{user_id}:{today}"


def append_message(session_id: str, role: ChatRole, content: str) -> None:
    """
    /** WHAT: append one message to the session and trim to MAX_HISTORY. **/
    """
    if not content:
        return
    entry: ChatMessage = {
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    key = _session_key(session_id)
    try:
        client = get_redis_client()
        pipe = client.pipeline()
        pipe.rpush(key, json.dumps(entry))
        pipe.ltrim(key, -MAX_HISTORY, -1)
        pipe.expire(key, SESSION_TTL_SECONDS)
        pipe.execute()
    except RedisError as exc:
        # /** WHY: chat is best-effort. Losing history is a papercut, not a
        #     reason to fail the request the user is currently making. **/
        logger.warning("chat.append_message: Redis error: %s", exc)


def get_history(session_id: str) -> list[ChatMessage]:
    """Return the ordered message list for a session. Empty on error/miss."""
    try:
        raws = get_redis_client().lrange(_session_key(session_id), 0, -1)
    except RedisError as exc:
        logger.warning("chat.get_history: Redis error: %s", exc)
        return []
    out: list[ChatMessage] = []
    for raw in raws or []:
        try:
            out.append(json.loads(raw))
        except (TypeError, ValueError):
            continue
    return out


def claim_budget(user_id: str) -> bool:
    """
    /** WHY: LLM calls cost real money. Users get a hard daily cap so a
        wandering script can't rack up a bill on your behalf. **/
    /** WHAT: atomically increment today's counter; return False if the
        result exceeded DAILY_MESSAGE_BUDGET. Sets an expiry on first
        increment so keys don't accumulate forever. **/
    """
    key = _budget_key(user_id)
    try:
        client = get_redis_client()
        pipe = client.pipeline()
        pipe.incr(key)
        # Expire tomorrow at midnight UTC. `expireat` with a computed
        # timestamp gives us the same effect as ttl-to-midnight without
        # any drift over the day.
        now = datetime.now(timezone.utc)
        tomorrow_midnight = int(datetime(
            now.year, now.month, now.day, tzinfo=timezone.utc,
        ).timestamp()) + 86400
        pipe.expireat(key, tomorrow_midnight)
        count, _ = pipe.execute()
        return int(count) <= DAILY_MESSAGE_BUDGET
    except RedisError as exc:
        # /** WHY: fail-open on Redis outage — this is a soft policy, not
        #     an authz decision. Better to answer a legitimate user than
        #     to lock everyone out during a Redis blip. **/
        logger.warning("chat.claim_budget: Redis error (allowing): %s", exc)
        return True
