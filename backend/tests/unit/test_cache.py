# tests/unit/test_cache.py
"""Unit tests for the cache-aside helper.

We rely on the autouse `fake_redis` fixture in tests/conftest.py, which swaps
the shared client for an in-memory fakeredis so these tests don't need a
network daemon.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import redis as redis_module
from app.utils import cache


# ---------------------------------------------------------------------------
# Basic get/set/invalidate contract
# ---------------------------------------------------------------------------

def test_set_then_get_roundtrips_json():
    cache.set_cached(("test", "hello"), {"a": 1, "b": [2, 3]}, ttl_seconds=30)
    assert cache.get_cached(("test", "hello")) == {"a": 1, "b": [2, 3]}


def test_get_missing_key_returns_none():
    assert cache.get_cached(("test", "missing")) is None


def test_set_uses_default_str_for_non_json_types():
    """UUIDs, datetimes etc must serialize (default=str) instead of blowing up."""
    import uuid, datetime
    uid = uuid.uuid4()
    ts = datetime.datetime(2026, 1, 2, 3, 4, 5)
    cache.set_cached(("test", "types"), {"uid": uid, "ts": ts}, ttl_seconds=30)
    got = cache.get_cached(("test", "types"))
    assert got == {"uid": str(uid), "ts": ts.isoformat()}


def test_invalidate_wipes_a_specific_key():
    cache.set_cached(("test", "keep"), "keep", ttl_seconds=30)
    cache.set_cached(("test", "drop"), "drop", ttl_seconds=30)
    cache.invalidate("test", "drop")

    assert cache.get_cached(("test", "drop")) is None
    assert cache.get_cached(("test", "keep")) == "keep"


def test_invalidate_pattern_wipes_matching_keys():
    cache.set_cached(("stories", "list", "page1"), 1, ttl_seconds=30)
    cache.set_cached(("stories", "list", "page2"), 2, ttl_seconds=30)
    cache.set_cached(("stories", "detail", "abc"), 3, ttl_seconds=30)

    cache.invalidate_pattern(("stories", "list", "*"))

    assert cache.get_cached(("stories", "list", "page1")) is None
    assert cache.get_cached(("stories", "list", "page2")) is None
    # Detail wasn't in the pattern.
    assert cache.get_cached(("stories", "detail", "abc")) == 3


def test_invalidate_story_kills_list_and_detail():
    story_id = "story-uuid-here"
    cache.set_cached(("stories", "list", "page1"), 1, ttl_seconds=30)
    cache.set_cached(("stories", "detail", story_id, "viewer=anon"), {"x": 1}, ttl_seconds=30)
    cache.set_cached(("stories", "detail", "other-id", "viewer=anon"), {"y": 1}, ttl_seconds=30)

    cache.invalidate_story(story_id)

    assert cache.get_cached(("stories", "list", "page1")) is None
    assert cache.get_cached(("stories", "detail", story_id, "viewer=anon")) is None
    # A different story's detail is untouched.
    assert cache.get_cached(("stories", "detail", "other-id", "viewer=anon")) == {"y": 1}


# ---------------------------------------------------------------------------
# Fail-soft on Redis errors
# ---------------------------------------------------------------------------

def test_get_returns_none_when_redis_errors(monkeypatch):
    boom = MagicMock()
    boom.get.side_effect = RedisConnectionError("redis is dead")
    monkeypatch.setattr(redis_module, "get_redis_client", lambda: boom)

    # get_cached must never propagate — cache misses are always survivable.
    assert cache.get_cached(("test", "any")) is None


def test_set_swallows_redis_errors(monkeypatch):
    boom = MagicMock()
    boom.setex.side_effect = RedisConnectionError("redis is dead")
    monkeypatch.setattr(redis_module, "get_redis_client", lambda: boom)

    # Should not raise — writes to the cache are best-effort.
    cache.set_cached(("test", "any"), "value", ttl_seconds=10)


def test_get_evicts_corrupt_payload():
    """A key holding non-JSON data must return None and get deleted."""
    from app.core.redis import get_redis_client
    client = get_redis_client()
    client.setex("cache:test:corrupt", 30, "definitely not json {")

    assert cache.get_cached(("test", "corrupt")) is None
    # Second read confirms it was evicted.
    assert client.exists("cache:test:corrupt") == 0
