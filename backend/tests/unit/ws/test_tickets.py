"""
/** WHY: tickets guard the WebSocket handshake. If mint/consume ever get
    the atomicity wrong, an attacker can replay one ticket to open many
    sockets or hijack a session. **/
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import redis as redis_module
from app.ws import tickets


def test_mint_ticket_stores_user_id_with_ttl(fake_redis):
    """A fresh ticket must land in Redis with the configured TTL."""
    uid = uuid.uuid4()
    token = tickets.mint_ticket(uid)
    assert token
    assert fake_redis.get(f"ws_ticket:{token}") == str(uid)
    ttl = fake_redis.ttl(f"ws_ticket:{token}")
    assert 0 < ttl <= tickets.TICKET_TTL_SECONDS


def test_consume_ticket_returns_user_and_deletes():
    """First consume returns the bound user; the ticket must be gone after."""
    uid = uuid.uuid4()
    token = tickets.mint_ticket(uid)
    assert tickets.consume_ticket(token) == str(uid)
    # Replay: same token must now be gone.
    assert tickets.consume_ticket(token) is None


def test_consume_unknown_ticket_returns_none():
    assert tickets.consume_ticket("nope") is None
    assert tickets.consume_ticket("") is None
    assert tickets.consume_ticket(None) is None  # type: ignore[arg-type]


def test_consume_fails_closed_on_redis_error(monkeypatch):
    """Unlike the rate limiter, ticket consumption is fail-CLOSED."""
    boom = MagicMock()
    boom.getdel.side_effect = RedisConnectionError("down")
    monkeypatch.setattr(redis_module, "get_redis_client", lambda: boom)

    assert tickets.consume_ticket("any-token") is None
