# tests/unit/test_rate_limiter.py
"""Unit tests for utils/rate_limiter — including the `request.client is None`
guard that was added after the audit surfaced an AttributeError risk under
ASGI transports that don't expose peer info (e.g. TestClient in some setups)."""

import os
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.utils import rate_limiter


class _FakeUrl:
    def __init__(self, path: str):
        self.path = path


def _fake_request(*, path: str = "/whatever", client_host: str | None = "1.2.3.4"):
    """Build a minimal Request-like object with just the attrs rate_limit reads."""
    client = SimpleNamespace(host=client_host) if client_host is not None else None
    return SimpleNamespace(client=client, url=_FakeUrl(path))


@pytest.fixture(autouse=True)
def _reset_log_and_env(monkeypatch):
    """Clear the in-memory limiter store + disable the E2E bypass for each test."""
    rate_limiter._request_log.clear()
    monkeypatch.delenv("E2E_TESTING", raising=False)
    yield
    rate_limiter._request_log.clear()


def test_rate_limit_allows_under_the_cap():
    """Calls below the limit should return None (no raise)."""
    req = _fake_request(path="/under-cap")
    for _ in range(3):
        assert rate_limiter.rate_limit(req, limit=5, window=60) is None


def test_rate_limit_blocks_once_cap_exceeded():
    """The (limit + 1)th call in the window must 429."""
    req = _fake_request(path="/blocked")
    for _ in range(2):
        rate_limiter.rate_limit(req, limit=2, window=60)

    with pytest.raises(HTTPException) as exc:
        rate_limiter.rate_limit(req, limit=2, window=60)
    assert exc.value.status_code == 429


def test_rate_limit_bypassed_when_e2e_testing(monkeypatch):
    """E2E_TESTING=true short-circuits the limiter so Cypress isn't rate-blocked."""
    monkeypatch.setenv("E2E_TESTING", "true")
    req = _fake_request(path="/e2e")
    # 100 hits at limit=1 would normally 429 immediately; here they must all pass.
    for _ in range(100):
        assert rate_limiter.rate_limit(req, limit=1, window=60) is None


def test_rate_limit_handles_missing_client_host():
    """Regression: `request.client` is None on some ASGI transports; the limiter
    used to crash with AttributeError instead of falling back to an "unknown"
    bucket. Now it should apply the limit under a synthetic key without raising."""
    req = _fake_request(client_host=None, path="/no-client")

    # First N calls fine…
    for _ in range(2):
        assert rate_limiter.rate_limit(req, limit=2, window=60) is None

    # …then the same "unknown" bucket 429s just like a real IP would.
    with pytest.raises(HTTPException) as exc:
        rate_limiter.rate_limit(req, limit=2, window=60)
    assert exc.value.status_code == 429


def test_rate_limit_keys_are_per_path():
    """Two different paths must not share the same limit bucket."""
    req_a = _fake_request(path="/route-a")
    req_b = _fake_request(path="/route-b")

    for _ in range(2):
        rate_limiter.rate_limit(req_a, limit=2, window=60)
    # /route-a is now full…
    with pytest.raises(HTTPException):
        rate_limiter.rate_limit(req_a, limit=2, window=60)
    # …but /route-b is still fresh.
    assert rate_limiter.rate_limit(req_b, limit=2, window=60) is None
