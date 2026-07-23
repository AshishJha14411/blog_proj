# tests/integration/test_rate_limit_routes.py
"""End-to-end proof that the Redis rate limiter fires on real routes.

The generic `_disable_rate_limits` fixture in test_auth_routes.py disables
throttling for the auth suite — this suite intentionally does NOT use that
override so we can assert the 429 behaviour.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_login_429_after_five_bad_attempts(client: TestClient, db_session: Session, monkeypatch, fake_redis):
    """Fifth failed login in a minute must 429 with a Retry-After header.

    The limit is 5/60s (see login_rate_limiter in utils/rate_limiter.py).
    We hit the endpoint with wrong credentials so it 401s until throttled.
    """
    # Make sure the E2E bypass is off — we're deliberately testing the limit.
    monkeypatch.delenv("E2E_TESTING", raising=False)

    # Opt out of the global _disable_all_rate_limiters fixture — this test
    # exists specifically to exercise the real login limiter.
    from app.utils import rate_limiter as rl
    client.app.dependency_overrides.pop(rl.login_rate_limiter, None)

    from tests.factories import RoleFactory
    RoleFactory(name="user")

    body = {"username": "no-such-user", "password": "definitely-wrong-pass"}

    # First 5 attempts: rate limiter allows through; login returns 401.
    for i in range(5):
        res = client.post("/auth/login", json=body)
        assert res.status_code == 401, f"attempt #{i+1}: {res.status_code} {res.text}"

    # 6th attempt: limiter kicks in before we even reach login_user.
    res = client.post("/auth/login", json=body)
    assert res.status_code == 429, res.text
    assert res.headers.get("Retry-After") == "60"
