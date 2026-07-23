"""Shared Redis client.

One connection pool per process, reused by the rate limiter (Phase 1),
cache-aside layer (Phase 1), Celery broker (Phase 2), and WS pub/sub
backplane (Phase 3). See UPGRADE_PLAN.md for the design rationale.

Design notes:
- `decode_responses=True` — we store JSON/text, not binary. Consumers get
  `str` back and don't have to `.decode()` everywhere.
- `socket_timeout=2` — a hung Redis must never wedge a request thread. The
  rate limiter is explicitly fail-open (see utils/rate_limiter.py), and the
  cache layer treats every Redis error as a cache miss.
- One shared client per process (lazy) so we don't leak connections when
  the app is imported repeatedly (tests do this).

The async client for the WebSocket handlers lives separately in Phase 3.
"""
from __future__ import annotations

import logging
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Return the process-wide Redis client (creating it lazily on first use)."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            health_check_interval=30,
        )
        logger.info("redis: connected to %s", _obfuscate_url(settings.REDIS_URL))
    return _client


def set_redis_client(client: redis.Redis) -> None:
    """Override the shared client — used by tests to inject fakeredis."""
    global _client
    _client = client


def reset_redis_client() -> None:
    """Drop the cached client. Only useful in test teardown."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:  # noqa: BLE001 — cleanup path
            pass
    _client = None


# FastAPI dependency form — routes can `Depends(get_redis)` if they want to
# unit-test with an override. Most call sites use `get_redis_client()`
# directly because they're not on the request path.
def get_redis() -> redis.Redis:
    return get_redis_client()


def _obfuscate_url(url: str) -> str:
    """Strip the password from a redis:// URL before logging it."""
    if "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    creds, host = rest.split("@", 1)
    return f"{scheme}://***@{host}"
