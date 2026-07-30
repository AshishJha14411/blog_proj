"""Outbound webhook endpoints.

WHY: webhooks are how you let other systems react to events in yours without
polling. A user registers a URL; when a subscribed event fires (e.g.
`story.published`), we POST a signed payload to it. "Signed" is the crux —
the receiver verifies an HMAC so it knows the call really came from us and
wasn't forged or replayed.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time import utcnow


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(String, nullable=False)
    # Shared secret used to HMAC-SHA256 sign each delivery. Generated server-side.
    secret = Column(String, nullable=False)
    # Which events this endpoint wants, as a JSON array of strings. Empty = all.
    event_types = Column(JSONB, nullable=False, default=list)

    active = Column(Boolean, nullable=False, default=True)
    # Delivery health: consecutive failures auto-disable a dead endpoint so we
    # don't retry a black hole forever.
    consecutive_failures = Column(Integer, nullable=False, default=0)
    disabled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User")
