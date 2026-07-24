"""Small cache-aside helper on top of the shared Redis client.

Design choices worth being able to defend:

- **Cache-aside** (a.k.a. "lazy"): read tries cache, miss goes to source, then
  populates cache. Simpler than write-through and gives us a *single*
  source of truth (the DB) — write-through duplicates the invariant.
- **Invalidation by DELETE, not UPDATE**: on write, wipe the affected keys.
  Trying to update a cached row correctly races with concurrent readers.
  Deleting is boring and safe: next read repopulates.
- **Fail-open on cache errors**: a Redis outage should degrade to
  "slightly slower reads", not "500 everywhere". Reads log + skip;
  writes to the cache are best-effort.
- **JSON payloads**, not pickle. Pickle over Redis is a foot-cannon
  (arbitrary-code deserialization from a shared cache = RCE).
- Namespacing lives in the key: `cache:stories:list:limit=10&offset=0`.
  A future `cache:` prefix bump is how we do "flush this cache class".

Not implemented here (future work): stampede protection (SETNX lock while
one worker recomputes), tag-based invalidation (`SADD tag:user:{uid}` +
`SMEMBERS` to build the wipe set). Ship this simpler version now.
"""
from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Callable, Iterable, Optional

from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


def _json_default(obj: Any) -> str:
    """Fallback serializer for json.dumps: ISO 8601 for dates/datetimes (matching
    how Pydantic already serializes them elsewhere in this app), str() for
    everything else (e.g. UUID)."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    return str(obj)

# Everything the cache writes lives under this prefix so we can namespace
# the whole layer with a single wildcard.
CACHE_PREFIX = "cache:"


def _k(*parts: str) -> str:
    """Compose a cache key. Callers pass semantic parts; this prefixes them."""
    return CACHE_PREFIX + ":".join(str(p) for p in parts)


def get_cached(key_parts: Iterable[str]) -> Optional[Any]:
    """Fetch a cached JSON value. Returns None on miss, error, or bad JSON."""
    key = _k(*key_parts)
    try:
        raw = get_redis_client().get(key)
    except RedisError as exc:
        logger.warning("cache.get: Redis error on %s: %s (returning miss)", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        # Corrupt/legacy entry — treat as miss and evict.
        logger.warning("cache.get: corrupt payload at %s, evicting", key)
        try:
            get_redis_client().delete(key)
        except RedisError:
            pass
        return None


def set_cached(key_parts: Iterable[str], value: Any, ttl_seconds: int) -> None:
    """Best-effort write. Silently drops on serialization or Redis error."""
    key = _k(*key_parts)
    try:
        payload = json.dumps(value, default=_json_default)
    except (TypeError, ValueError) as exc:
        logger.warning("cache.set: value at %s not JSON-serializable: %s", key, exc)
        return
    try:
        get_redis_client().setex(key, ttl_seconds, payload)
    except RedisError as exc:
        logger.warning("cache.set: Redis error on %s: %s", key, exc)


def invalidate(*key_parts: str) -> None:
    """Delete one cache entry by its parts."""
    try:
        get_redis_client().delete(_k(*key_parts))
    except RedisError as exc:
        logger.warning("cache.invalidate: Redis error: %s", exc)


def invalidate_pattern(pattern_parts: Iterable[str]) -> None:
    """
    Wipe every key matching a pattern (SCAN + DEL, no KEYS — keeps prod safe).

    Use for group invalidations like "all story-list pages". Pass the parts
    with `*` in the wildcard positions, e.g. `("stories", "list", "*")`.
    """
    pattern = _k(*pattern_parts)
    try:
        client = get_redis_client()
        # SCAN is O(N) but non-blocking on the Redis server — safe on prod.
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
    except RedisError as exc:
        logger.warning("cache.invalidate_pattern(%s): Redis error: %s", pattern, exc)


# ---------------------------------------------------------------------------
# Domain-specific helpers — thin wrappers so the callers read cleanly.
# Story-list cache is intentionally per-page (list_limit_offset key parts).
# ---------------------------------------------------------------------------

STORY_LIST_TTL = 60  # seconds — the read-you-just-published tolerance
STORY_DETAIL_TTL = 60


def story_list_key(*, limit: int, offset: int, tag: Optional[str], author_id: Optional[str], viewer: str) -> tuple[str, ...]:
    """
    Build the cache key parts for a story-list request. The viewer identity
    is baked in because mods see unpublished stories and normal users don't;
    caching one response and serving it to the other would leak drafts.
    """
    return (
        "stories",
        "list",
        f"limit={limit}",
        f"offset={offset}",
        f"tag={tag or '_'}",
        f"author={author_id or '_'}",
        f"viewer={viewer}",
    )


def story_detail_key(*, story_id: str, viewer: str) -> tuple[str, ...]:
    return ("stories", "detail", story_id, f"viewer={viewer}")


def invalidate_story(story_id: str) -> None:
    """
    Wipe every cache entry touching this story. Called on
    create/update/delete/publish/unpublish/moderate.
    """
    invalidate_pattern(("stories", "list", "*"))
    invalidate_pattern(("stories", "detail", story_id, "*"))
