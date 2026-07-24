"""
/** WHY: WebSocket delivery needs to fan out across every backend instance,
    not just the one that owns the socket. A user connected to instance A
    will never see events created on instance B unless the two instances
    share a backplane. Redis pub/sub is the standard cheap backplane. **/

/** WHAT: `ConnectionManager` tracks the sockets attached to THIS process,
    plus a background task subscribed to `notify:{user_id}` channels. When
    any writer PUBLISHes to that channel — from a route handler, a Celery
    task, wherever — every listening ConnectionManager relays the payload
    to its own local sockets. **/

/** WHY-THIS-WAY:
    - `dict[user_id, set[WebSocket]]` for local state — a user can be on
      multiple tabs, each with its own socket.
    - Async client for pub/sub so we can await `pubsub.get_message()` in
      the same event loop as the FastAPI request handler.
    - Broadcast wraps every per-socket send in try/except so ONE dead
      socket can't kill the fanout for everyone else on this instance. **/
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Optional

import redis.asyncio as aioredis
from fastapi import WebSocket
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

NOTIFY_CHANNEL_PREFIX = "notify:"


def notify_channel(user_id: str) -> str:
    return f"{NOTIFY_CHANNEL_PREFIX}{user_id}"


class ConnectionManager:
    """Per-process socket registry with a Redis-pubsub fanout tail."""

    def __init__(self) -> None:
        # user_id (str) -> set of live sockets on this process
        self._sockets: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._pubsub_task: Optional[asyncio.Task] = None
        # recommended by claude opus 4.7: build the async client lazily. If
        # the app never opens a WS, we never open the pub/sub connection.
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        """
        /** WHAT: register a socket. Starts the shared pub/sub subscriber
            on the first connect. **/
        """
        await ws.accept()
        async with self._lock:
            self._sockets[user_id].add(ws)
            if self._pubsub_task is None or self._pubsub_task.done():
                self._pubsub_task = asyncio.create_task(self._pubsub_loop())

    async def disconnect(self, user_id: str, ws: WebSocket) -> None:
        """Remove a socket. Best-effort — never raises."""
        async with self._lock:
            sockets = self._sockets.get(user_id)
            if sockets:
                sockets.discard(ws)
                if not sockets:
                    self._sockets.pop(user_id, None)

    async def send_local(self, user_id: str, payload: dict) -> None:
        """
        /** WHAT: deliver a payload to every socket for this user on THIS
            instance. Called by the pub/sub loop. **/
        /** WHY-THIS-WAY: each send is wrapped so a single broken socket
            (client walked away without a close frame) doesn't abort the
            fanout to the rest of the user's tabs. **/
        """
        sockets = list(self._sockets.get(user_id, set()))
        if not sockets:
            return
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.debug("ws.send_local: dropping socket for %s: %s", user_id, exc)
                await self.disconnect(user_id, ws)

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            # recommended by claude opus 4.7: separate connection for pub/sub —
            # you cannot share the connection with other commands, and mixing
            # them is a well-documented redis-py pitfall.
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=None,           # pubsub blocks; do not time it out
                socket_connect_timeout=5,
            )
        return self._redis

    async def _pubsub_loop(self) -> None:
        """
        /** WHY: single subscription to `notify:*` so we don't spin up a
            new pubsub per user. Redis handles per-channel routing internally. **/
        """
        try:
            r = await self._get_redis()
            pubsub = r.pubsub()
            await pubsub.psubscribe(f"{NOTIFY_CHANNEL_PREFIX}*")
            async for message in pubsub.listen():
                if message is None or message.get("type") != "pmessage":
                    continue
                channel = message["channel"]
                # Strip prefix -> user id
                user_id = channel[len(NOTIFY_CHANNEL_PREFIX):]
                raw = message["data"]
                try:
                    payload = json.loads(raw) if isinstance(raw, str) else raw
                except (TypeError, ValueError):
                    logger.warning("ws pubsub: bad payload on %s: %r", channel, raw)
                    continue
                await self.send_local(user_id, payload)
        except asyncio.CancelledError:
            raise
        except RedisError as exc:
            logger.error("ws pubsub loop terminated: %s", exc)


# Module-level singleton — ConnectionManager keeps per-process state, so
# every request/task in this process shares the same instance.
manager = ConnectionManager()


def publish(user_id: str, payload: dict) -> None:
    """
    /** WHY: any code path that wants to push to a user (notify(),
        moderation task, chat handler) calls this ONE function. It uses the
        sync Redis client so callers don't have to be async. **/
    /** WHAT: PUBLISH a JSON payload on the user's channel. Fire-and-forget
        by design — if there's no subscriber, Redis just drops it, which is
        the correct behavior for "user isn't connected right now". **/
    """
    from app.core.redis import get_redis_client
    try:
        get_redis_client().publish(notify_channel(user_id), json.dumps(payload, default=str))
    except RedisError as exc:
        # A publish failure is not a request failure — the REST API and DB
        # writes already succeeded. Just log so ops sees the outage.
        logger.warning("ws.publish: Redis error for user %s: %s", user_id, exc)
