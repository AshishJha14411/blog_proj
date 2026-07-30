"""Idempotency-Key middleware for safe retries on unsafe POSTs.

WHY: a client that POSTs `/stories` and loses the connection can't know if the
story was created. Retrying risks a duplicate. The industry fix (Stripe's
model): the client sends an `Idempotency-Key` header; the server records the
first response under that key and *replays* it on any retry, so the operation
happens at most once regardless of how many times the client sends it.

WHY-THIS-WAY:
- Opt-in: only POSTs that carry the header are affected — nothing else changes.
- Redis `SET NX` is the claim primitive. First caller wins and processes; a
  concurrent duplicate sees the in-flight marker and gets 409 (don't double-run).
- A completed request stores {status, body, media_type}; replays return it
  verbatim with `Idempotency-Replayed: true`.
- Fail-OPEN: if Redis is unreachable we let the request through unguarded,
  matching the rate limiter — availability over the idempotency guarantee.
- Streaming responses (SSE) are never buffered/cached — they're excluded.
"""
from __future__ import annotations

import hashlib
import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.redis import get_redis_client

logger = logging.getLogger("app")

_TTL_SECONDS = 24 * 3600
_IN_FLIGHT = "\x00in-flight"  # sentinel that can't collide with a JSON body


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)
        key = request.headers.get("idempotency-key")
        if not key:
            return await call_next(request)

        redis_key = _redis_key(request, key)
        try:
            client = get_redis_client()
            claimed = client.set(redis_key, _IN_FLIGHT, nx=True, ex=_TTL_SECONDS)
        except Exception as exc:  # noqa: BLE001 — fail open, same as rate limiter
            logger.warning("idempotency: redis unavailable, passing through: %s", exc)
            return await call_next(request)

        if not claimed:
            return self._replay_or_conflict(client, redis_key)

        # First time we've seen this key — run the request, then cache it.
        response = await call_next(request)

        # Never buffer a stream (SSE); release the claim so a genuine retry can
        # run rather than being stuck behind a non-cacheable in-flight marker.
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("text/event-stream"):
            try:
                client.delete(redis_key)
            except Exception:  # noqa: BLE001
                pass
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Only cache success-ish responses; on error, drop the claim so the
        # client can legitimately retry the operation.
        if response.status_code < 400:
            try:
                client.set(
                    redis_key,
                    json.dumps(
                        {
                            "status": response.status_code,
                            "body": body.decode("utf-8", "replace"),
                            "media_type": content_type or "application/json",
                        }
                    ),
                    ex=_TTL_SECONDS,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("idempotency: failed to cache response: %s", exc)
        else:
            try:
                client.delete(redis_key)
            except Exception:  # noqa: BLE001
                pass

        # Rebuild the response since we consumed its body_iterator.
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=content_type or None,
        )

    @staticmethod
    def _replay_or_conflict(client, redis_key: str) -> Response:
        try:
            stored = client.get(redis_key)
        except Exception:  # noqa: BLE001
            stored = None
        if stored == _IN_FLIGHT or stored is None:
            # The original is still running (or vanished mid-flight).
            return JSONResponse(
                status_code=409,
                media_type="application/problem+json",
                content={
                    "type": "https://quillandcode.dev/errors/idempotency-conflict",
                    "title": "Conflict",
                    "status": 409,
                    "detail": "A request with this Idempotency-Key is still being processed.",
                },
            )
        cached = json.loads(stored)
        return Response(
            content=cached["body"],
            status_code=cached["status"],
            media_type=cached.get("media_type", "application/json"),
            headers={"Idempotency-Replayed": "true"},
        )


def _redis_key(request: Request, idempotency_key: str) -> str:
    """Scope the key by caller so two users can't read each other's cached
    response. We hash the bearer token (if any) rather than decode it here —
    no JWT coupling in the middleware — falling back to client IP for anon."""
    auth = request.headers.get("authorization", "")
    if auth:
        ident = hashlib.sha256(auth.encode()).hexdigest()[:16]
    else:
        ident = request.client.host if request.client else "anon"
    scope = f"{ident}:{request.url.path}:{idempotency_key}"
    return "idem:" + hashlib.sha256(scope.encode()).hexdigest()
