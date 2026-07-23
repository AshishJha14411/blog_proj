# tests/unit/test_rate_limiter.py
"""Unit tests for the Redis-backed rate limiter.

Previous incarnation was in-process and had a `_request_log` dict; this file
now exercises the fakeredis-backed sliding-window implementation. The public
signature (`rate_limit(request, limit, window)`) hasn't changed.
"""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

from app.utils import rate_limiter
from app.core import redis as redis_module


class _FakeUrl:
    def __init__(self, path: str):
        self.path = path


def _fake_request(*, path: str = "/whatever", client_host: str | None = "1.2.3.4"):
    """Minimal Request-like object with just the attrs rate_limit reads."""
    client = SimpleNamespace(host=client_host) if client_host is not None else None
    return SimpleNamespace(client=client, url=_FakeUrl(path))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, fake_redis):
    """Each test starts with an empty Redis and the E2E bypass off."""
    monkeypatch.delenv("E2E_TESTING", raising=False)
    fake_redis.flushall()
    yield
    fake_redis.flushall()


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_rate_limit_allows_under_the_cap():
    req = _fake_request(path="/under-cap")
    for _ in range(3):
        assert rate_limiter.rate_limit(req, limit=5, window=60) is None


def test_rate_limit_blocks_once_cap_exceeded():
    """The (limit + 1)th call in the window must 429 with a Retry-After header."""
    req = _fake_request(path="/blocked")
    for _ in range(2):
        rate_limiter.rate_limit(req, limit=2, window=60)

    with pytest.raises(HTTPException) as exc:
        rate_limiter.rate_limit(req, limit=2, window=60)
    assert exc.value.status_code == 429
    assert exc.value.headers is not None
    assert exc.value.headers.get("Retry-After") == "60"


def test_rate_limit_keys_are_per_scope():
    """Two different scopes (paths, by default) share nothing."""
    req_a = _fake_request(path="/route-a")
    req_b = _fake_request(path="/route-b")

    for _ in range(2):
        rate_limiter.rate_limit(req_a, limit=2, window=60)
    with pytest.raises(HTTPException):
        rate_limiter.rate_limit(req_a, limit=2, window=60)
    # /route-b is still fresh.
    assert rate_limiter.rate_limit(req_b, limit=2, window=60) is None


def test_rate_limit_identity_beats_ip():
    """Passing `identity=` uses the user id instead of the client IP."""
    req = _fake_request(path="/mixed", client_host="1.2.3.4")

    # Same request object, two different users, each gets their own bucket.
    for _ in range(2):
        rate_limiter.rate_limit(req, limit=2, window=60, identity="alice")
    for _ in range(2):
        rate_limiter.rate_limit(req, limit=2, window=60, identity="bob")

    # Alice hits her cap independently.
    with pytest.raises(HTTPException):
        rate_limiter.rate_limit(req, limit=2, window=60, identity="alice")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_rate_limit_handles_missing_client_host():
    """`request.client` is None on some ASGI transports; the limiter must
    still work under a synthetic 'unknown' identity instead of crashing."""
    req = _fake_request(client_host=None, path="/no-client")

    for _ in range(2):
        assert rate_limiter.rate_limit(req, limit=2, window=60) is None

    with pytest.raises(HTTPException) as exc:
        rate_limiter.rate_limit(req, limit=2, window=60)
    assert exc.value.status_code == 429


def test_rate_limit_sliding_window_forgets_old_entries(fake_redis):
    """After the window elapses, prior hits must be discarded so callers can hit again."""
    req = _fake_request(path="/slide")

    # Fill the bucket with entries scored 10 minutes ago; they should be swept
    # by the zremrangebyscore call on the next attempt.
    key = "rl:/slide:ip:1.2.3.4"
    now_ms = int(time.time() * 1000)
    stale_ms = now_ms - (10 * 60 * 1000)
    for i in range(5):
        fake_redis.zadd(key, {f"stale{i}": stale_ms})

    # Even at limit=2 window=60, the stale entries are cleaned out first,
    # so this request is the first fresh one.
    assert rate_limiter.rate_limit(req, limit=2, window=60) is None
    assert rate_limiter.rate_limit(req, limit=2, window=60) is None
    with pytest.raises(HTTPException):
        rate_limiter.rate_limit(req, limit=2, window=60)


# ---------------------------------------------------------------------------
# E2E bypass rules
# ---------------------------------------------------------------------------

def test_e2e_bypass_disables_limiting_when_not_in_production(monkeypatch):
    monkeypatch.setenv("E2E_TESTING", "true")
    req = _fake_request(path="/e2e")
    for _ in range(50):
        assert rate_limiter.rate_limit(req, limit=1, window=60) is None


def test_e2e_bypass_ignored_in_production(monkeypatch):
    """A stray E2E_TESTING=true on the prod host must not switch off throttling."""
    from app.core.config import settings
    monkeypatch.setenv("E2E_TESTING", "true")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    req = _fake_request(path="/e2e-prod")
    rate_limiter.rate_limit(req, limit=1, window=60)
    with pytest.raises(HTTPException):
        rate_limiter.rate_limit(req, limit=1, window=60)


# ---------------------------------------------------------------------------
# Fail-open behaviour
# ---------------------------------------------------------------------------

def test_rate_limit_fails_open_when_redis_is_down(monkeypatch):
    """If Redis pipeline calls raise, the limiter must log and allow the request.
    A rate limiter must never itself become the outage."""

    class _BoomPipe:
        def zremrangebyscore(self, *a, **kw): return self
        def zadd(self, *a, **kw): return self
        def zcard(self, *a, **kw): return self
        def expire(self, *a, **kw): return self
        def execute(self):
            raise RedisConnectionError("redis is on fire")

    boom_client = MagicMock()
    boom_client.pipeline.return_value = _BoomPipe()
    monkeypatch.setattr(redis_module, "get_redis_client", lambda: boom_client)

    req = _fake_request(path="/fail-open")
    # No exception, even far above the "limit".
    for _ in range(10):
        assert rate_limiter.rate_limit(req, limit=1, window=60) is None
