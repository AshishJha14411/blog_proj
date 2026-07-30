from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# Known event names. Kept as a constant so routes can validate and docs can
# list them; empty subscription means "all events".
KNOWN_EVENTS = {"story.published", "story.rejected"}


class WebhookCreate(BaseModel):
    url: HttpUrl
    event_types: List[str] = Field(default_factory=list)


class WebhookOut(BaseModel):
    id: UUID
    url: str
    event_types: List[str]
    active: bool
    consecutive_failures: int
    created_at: Optional[datetime] = None

    model_config = dict(from_attributes=True)


class WebhookCreated(WebhookOut):
    # The signing secret is returned ONCE, at creation. Never on list/get —
    # same rule as an API key. The receiver stores it to verify signatures.
    secret: str
