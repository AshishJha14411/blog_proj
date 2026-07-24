"""
/** WHY: Celery guarantees *at-least-once* delivery (see task_acks_late in
    app/worker.py). That means the same task can legitimately run twice —
    for example if the worker crashes right after emailing but before ACKing,
    the broker re-delivers and a second worker sends the email again. **/

/** WHAT: `claim_once(key, ttl)` returns True the first time a given key is
    seen inside the TTL window, False every subsequent time. Callers wrap
    the "side effect" they want to happen exactly once. **/

/** WHY-THIS-WAY: SET key value NX EX ttl is atomic — no race between check
    and set. The alternative (GET then SET) has a window in which two workers
    both see "unset" and both write. Failing-open on Redis errors is fine
    for MOST cases (we'd rather send an email twice than never), but if you
    want fail-closed behavior for a specific caller pass `on_error="deny"`. **/
"""
from __future__ import annotations

import logging
from typing import Literal

from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# 24h default. Idempotency keys are cheap; the risk of collisions ranks well
# below the risk of forgetting to expire a key and holding onto stale state.
DEFAULT_TTL_SECONDS = 60 * 60 * 24


def claim_once(
    key: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    *,
    on_error: Literal["allow", "deny"] = "allow",
) -> bool:
    """
    /** WHAT: attempt to atomically reserve `key` for this run.
        Returns True if the caller now owns the key (i.e. this is the first
        time we've seen it in the TTL window); False if someone else already
        holds it (a duplicate). **/

    /** Callers should shape their side effect like:

            if not claim_once(f"email:{message_id}"):
                return  # duplicate delivery — silently succeed

            do_the_side_effect()

        Silently returning on a duplicate is intentional: from Celery's
        perspective the task succeeded (the desired end-state is achieved).
        Raising would cause a retry, which recreates the exact duplicate we
        just avoided. **/

    /** WHY-THIS-WAY: SET NX EX in one call, not GET-then-SET. The Redis
        docs are explicit that this is the atomic pattern for "do this once".
        The `on_error` knob lets high-risk callers (payments) demand a
        successful reservation before proceeding — the default is
        "allow" because for emails/notifications a second send is a papercut,
        while dropping a legitimate first send is a real problem. **/
    """
    fq_key = f"idemp:{key}"
    try:
        # recommended by claude opus 4.7: NX means "only set if not exists".
        # The client returns True if the key was set, False otherwise.
        # `nx=True, ex=ttl_seconds` is atomic on the Redis server.
        acquired = get_redis_client().set(fq_key, "1", nx=True, ex=ttl_seconds)
        return bool(acquired)
    except RedisError as exc:
        logger.error("idempotency.claim_once: Redis error on %r: %s", key, exc)
        # Default is fail-open: allow the caller to run so we don't drop
        # legitimate work during a Redis outage. Callers that can't tolerate
        # a duplicate can pass on_error="deny".
        return on_error == "allow"


def release(key: str) -> None:
    """
    /** WHAT: forget an idempotency claim before its TTL runs out.
        Rarely needed — the TTL handles the common case. Useful in tests
        and for retriable operations where the claimed run definitively
        failed and you want to allow a fresh caller to try. **/
    """
    try:
        get_redis_client().delete(f"idemp:{key}")
    except RedisError as exc:
        logger.warning("idempotency.release: Redis error on %r: %s", key, exc)
