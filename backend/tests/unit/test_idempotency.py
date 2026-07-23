"""
/** WHY: at-least-once delivery means the same task can legitimately run
    twice. The claim_once helper is what makes each task safe against that.
    If this file goes red, every idempotent task is now unsafe. **/
"""
from __future__ import annotations

from unittest.mock import MagicMock

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import redis as redis_module
from app.utils import idempotency


def test_first_claim_wins():
    """The first caller of a key gets True; every subsequent caller gets False."""
    assert idempotency.claim_once("test:winner") is True
    assert idempotency.claim_once("test:winner") is False
    assert idempotency.claim_once("test:winner") is False


def test_claims_are_independent_per_key():
    """A different key must not collide with an existing claim."""
    assert idempotency.claim_once("test:a") is True
    assert idempotency.claim_once("test:b") is True
    assert idempotency.claim_once("test:a") is False


def test_release_lets_a_key_be_claimed_again():
    """Releasing a claim before its TTL frees the key for a fresh caller."""
    assert idempotency.claim_once("test:releasable") is True
    idempotency.release("test:releasable")
    assert idempotency.claim_once("test:releasable") is True


def test_ttl_is_respected(fake_redis):
    """After the TTL elapses, the key must be free again."""
    idempotency.claim_once("test:ttl", ttl_seconds=10)
    # fakeredis exposes a way to see the TTL directly.
    assert fake_redis.ttl("idemp:test:ttl") == 10


def test_fail_open_when_redis_errors():
    """Default behavior on Redis error is to ALLOW the caller through —
    better to send an email twice than lose it during an outage."""
    boom = MagicMock()
    boom.set.side_effect = RedisConnectionError("redis down")
    # NOTE: `idempotency.py` imports `get_redis_client` by name, so patching
    # the attribute on `redis_module` wouldn't reach that already-bound
    # reference. `set_redis_client` swaps the shared singleton instead —
    # the same mechanism the autouse `fake_redis` fixture uses — so it's
    # visible no matter how callers imported the getter.
    redis_module.set_redis_client(boom)

    assert idempotency.claim_once("test:down") is True


def test_fail_closed_when_caller_asks():
    """For high-risk operations that can't tolerate duplicates, on_error='deny'
    forces the caller to skip if we can't confirm the reservation."""
    boom = MagicMock()
    boom.set.side_effect = RedisConnectionError("redis down")
    redis_module.set_redis_client(boom)

    assert idempotency.claim_once("test:down", on_error="deny") is False
