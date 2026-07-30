"""Webhook management + event dispatch.

Split of responsibilities:
- CRUD (`create_endpoint`, `list_endpoints`, `delete_endpoint`) — user manages
  their own endpoints.
- `sign_body` — the HMAC-SHA256 primitive, shared by the delivery task and by
  any test receiver so signing/verification stay in lockstep.
- `dispatch_event` — fan an event out to every subscribed, active endpoint by
  enqueuing one delivery task each (so a slow/dead receiver can't block the
  caller or the other receivers).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.webhook import WebhookEndpoint
from app.models.user import User
from app.schemas.webhook import WebhookCreate, KNOWN_EVENTS


def sign_body(secret: str, body: bytes) -> str:
    """Return the hex HMAC-SHA256 of `body` under `secret`.

    The receiver recomputes this over the raw request body and compares with
    `hmac.compare_digest` (constant-time) to authenticate the delivery.
    """
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def serialize_event(event: str, payload: dict) -> bytes:
    """Canonical JSON bytes for an event — signed AND sent, byte-for-byte, so
    the signature the receiver verifies matches exactly what it received."""
    envelope = {"event": event, "data": payload}
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True, default=str).encode()


def create_endpoint(db: Session, user: User, data: WebhookCreate) -> WebhookEndpoint:
    unknown = [e for e in data.event_types if e not in KNOWN_EVENTS]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event types: {', '.join(unknown)}. Known: {', '.join(sorted(KNOWN_EVENTS))}",
        )
    endpoint = WebhookEndpoint(
        user_id=user.id,
        url=str(data.url),
        secret="whsec_" + secrets.token_urlsafe(32),
        event_types=data.event_types,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


def list_endpoints(db: Session, user: User) -> List[WebhookEndpoint]:
    return (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.user_id == user.id)
        .order_by(WebhookEndpoint.created_at.desc())
        .all()
    )


def delete_endpoint(db: Session, user: User, endpoint_id: uuid.UUID) -> None:
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.user_id == user.id)
        .first()
    )
    if not endpoint:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Webhook endpoint not found")
    db.delete(endpoint)
    db.commit()


def dispatch_event(db: Session, event: str, payload: dict) -> int:
    """Enqueue delivery of `event` to every active endpoint subscribed to it.

    Returns the number of deliveries enqueued. Import the task lazily so this
    module (used from the request path) doesn't pull Celery into its import
    graph at load time.
    """
    from app.tasks.webhook import deliver_webhook_task

    endpoints = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.active.is_(True))
        .all()
    )
    count = 0
    for ep in endpoints:
        # Empty subscription = all events; otherwise must include this event.
        if ep.event_types and event not in ep.event_types:
            continue
        deliver_webhook_task.delay(endpoint_id=str(ep.id), event=event, payload=payload)
        count += 1
    return count
