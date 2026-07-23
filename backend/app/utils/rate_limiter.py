"""Redis-backed sliding-window rate limiter.

Replaces the previous in-process `defaultdict[deque]` implementation which:
- reset on every worker restart (G9 in FINDINGS),
- gave each Gunicorn worker its own bucket (limit × N workers effective),
- had unbounded memory (dead keys never evicted),
- crashed when `request.client` was None.

Design decisions worth being able to defend in an interview:

1. **Sliding window via sorted set** (ZSET), not fixed-window INCR. A fixed
   window allows 2× the limit at the boundary (last second of window N +
   first second of N+1); the ZSET is exact at any point in time. Cost:
   O(log N) per op and one entry per request. Worth it — abuse traffic
   spikes at exactly those boundaries.

2. **Fail-open**. If Redis is unreachable, log and allow the request. A
   rate limiter must never become the outage. Authz would be fail-closed
   for the opposite reason.

3. **Identity**: per-user for authenticated routes, per-IP for anonymous.
   IP-only would punish shared NATs (schools, offices, mobile carriers).
   The caller picks by passing `identity` — the default falls back to IP.

4. **E2E bypass** kept — but explicitly refused when
   `ENVIRONMENT=production`. A stray `E2E_TESTING=true` on the live host
   must not disable throttling everywhere.

5. **Public interface unchanged**: `rate_limit(request, limit, window)` and
   `signup_rate_limiter(request)` still exist so the swap is drop-in for
   existing routes and tests can still `dependency_overrides` them.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bypass switch
# ---------------------------------------------------------------------------

def _bypass_enabled() -> bool:
    """
    Return True iff the E2E bypass is active AND we're not in production.
    """
    if settings.ENVIRONMENT.lower() == "production":
        return False
    return os.getenv("E2E_TESTING") == "true"


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

def _identity_from_request(request: Request, identity: Optional[str]) -> str:
    """Prefer an explicit identity (usually user id). Fall back to client IP."""
    if identity:
        return f"u:{identity}"
    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def _check_limit(
    scope: str,
    identity_key: str,
    *,
    limit: int,
    window: int,
) -> None:
    """
    Enforce `limit` requests per `window` seconds under (scope, identity).
    Sliding window via a ZSET keyed by the request timestamp.

    Raises HTTPException(429) if the limit is exceeded. Silently returns
    (fail-open) if Redis is unreachable.
    """
    key = f"rl:{scope}:{identity_key}"
    now_ms = int(time.time() * 1000)
    window_ms = window * 1000
    cutoff = now_ms - window_ms

    try:
        client = get_redis_client()
        pipe = client.pipeline()
        # 1) Drop entries that fell out of the window.
        pipe.zremrangebyscore(key, 0, cutoff)
        # 2) Record this attempt. Score = ms timestamp, member = unique id so
        #    two requests in the same ms don't collide into one ZSET entry.
        pipe.zadd(key, {f"{now_ms}:{uuid.uuid4().hex}": now_ms})
        # 3) Count what's left in the window.
        pipe.zcard(key)
        # 4) Extend the TTL so idle keys eventually vanish.
        pipe.expire(key, window + 1)
        _, _, count, _ = pipe.execute()
    except RedisError as exc:
        # FAIL-OPEN. Log loudly so ops notices, but let the request through.
        logger.error("rate_limit: Redis unavailable, allowing request: %s", exc)
        return

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please try again later.",
            headers={"Retry-After": str(window)},
        )


# ---------------------------------------------------------------------------
# Public API — same shape the routes already use
# ---------------------------------------------------------------------------

def rate_limit(
    request: Request,
    *,
    limit: int = 5,
    window: int = 60,
    scope: Optional[str] = None,
    identity: Optional[str] = None,
) -> None:
    """
    Per-IP (or per-user) sliding window limit for the current route.

    Kept intentionally compatible with the old signature so existing routes
    (`Depends(rate_limit)`) and test overrides
    (`app.dependency_overrides[rate_limit] = ...`) keep working.

    - `scope`: bucket name — defaults to the URL path so different routes
      don't share a limit. Pass a stable name when you want two routes to
      share a bucket (e.g. login + forgot-password abuse from the same IP).
    - `identity`: pass the user id when the route is authenticated. Anon
      calls default to the client IP.
    """
    if _bypass_enabled():
        return

    scope = scope or request.url.path
    identity_key = _identity_from_request(request, identity)
    _check_limit(scope, identity_key, limit=limit, window=window)


def signup_rate_limiter(request: Request) -> None:
    """Named dependency used by the /auth/signup route.

    Kept as a separate symbol so tests can override just this one endpoint
    without touching the generic `rate_limit` used by everything else. The
    3/hour cap matches the table in UPGRADE_PLAN Phase 1.
    """
    rate_limit(request, limit=3, window=3600, scope="auth:signup")


# ---------------------------------------------------------------------------
# Ready-made dependency builders for the config-driven table
# ---------------------------------------------------------------------------
# Each helper is a factory: `Depends(login_rate_limiter)` in the route.
# Split out from a single generic factory so FastAPI's dependency identity
# stays stable per route (each helper is one function object) — this makes
# `app.dependency_overrides[login_rate_limiter] = ...` work in tests.

def login_rate_limiter(request: Request) -> None:
    rate_limit(request, limit=5, window=60, scope="auth:login")


def forgot_password_rate_limiter(request: Request) -> None:
    # B15: without this, an attacker can flood a target's inbox.
    rate_limit(request, limit=3, window=3600, scope="auth:forgot")


def story_create_rate_limiter(request: Request) -> None:
    rate_limit(request, limit=10, window=3600, scope="story:create")


def llm_generate_rate_limiter(request: Request) -> None:
    # LLM = money. This is a per-IP cap on anon; routes may layer a per-user
    # cap on top using rate_limit(..., identity=str(current_user.id)).
    rate_limit(request, limit=5, window=3600, scope="story:generate")


def comment_create_rate_limiter(request: Request) -> None:
    rate_limit(request, limit=30, window=3600, scope="comment:create")


def flag_rate_limiter(request: Request) -> None:
    rate_limit(request, limit=20, window=3600, scope="flag:create")
