"""
/** WHY: putting the JWT in a WebSocket URL is a well-known footgun — URLs
    land in proxy access logs, browser history, and referer headers. The
    industry pattern is: authenticated HTTP POST mints a short-lived
    single-use ticket; the WS handshake presents the ticket instead. **/

/** WHAT: `mint_ticket(user_id)` returns an opaque token stored in Redis
    with 30s TTL. `consume_ticket(token)` atomically reads-and-deletes it
    (GETDEL) so a ticket can never be replayed. **/

/** WHY-THIS-WAY: GETDEL is atomic — no race between "was this valid?" and
    "is it now consumed?". Two clients presenting the same ticket in the
    same millisecond: exactly one wins. **/
"""
from __future__ import annotations

import logging
import secrets
import uuid
from typing import Optional

from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# 30 seconds. Long enough for the client to make the WS handshake, short
# enough that a stolen ticket has no useful lifespan.
TICKET_TTL_SECONDS = 30

# recommended by claude opus 4.7: `secrets.token_urlsafe(32)` gives 256 bits
# of entropy in a URL-safe form. 32 chars is overkill for a 30s ticket but
# free — no reason to skimp.
TOKEN_BYTES = 32


def _key(token: str) -> str:
    return f"ws_ticket:{token}"


def mint_ticket(user_id: uuid.UUID | str) -> str:
    """
    /** WHY: hand the client a ticket to present on WS connect. **/
    /** WHAT: creates a random token bound to user_id in Redis with TTL. **/
    """
    token = secrets.token_urlsafe(TOKEN_BYTES)
    client = get_redis_client()
    client.set(_key(token), str(user_id), ex=TICKET_TTL_SECONDS)
    return token


def consume_ticket(token: str) -> Optional[str]:
    """
    /** WHAT: atomically read-and-delete a ticket. Returns the bound user id,
        or None if the token is unknown / expired / already used. **/
    /** WHY-THIS-WAY: GETDEL is Redis 6.2+. It removes the race we'd get with
        GET-then-DEL where two connectors could see the same value. **/
    """
    if not token:
        return None
    try:
        # `getdel` is a first-class command on redis-py 4.0+.
        return get_redis_client().getdel(_key(token))
    except RedisError as exc:
        logger.warning("ws.tickets.consume: Redis error: %s", exc)
        # /** WHY: fail-CLOSED here — refusing to authenticate a WS connection
        #     during a Redis blip is safer than admitting unknown callers. **/
        return None
