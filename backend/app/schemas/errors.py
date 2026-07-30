"""RFC 7807 `application/problem+json` error envelope.

WHY: the app currently returns ad-hoc `{"detail": "..."}` bodies, and the
shape drifts (sometimes a string, sometimes a list from validation errors).
Consumers can't rely on it. RFC 7807 defines ONE machine-readable error shape
(`type`, `title`, `status`, `detail`, `instance`) so any client — the frontend,
a webhook receiver, a test — parses errors the same way every time.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ProblemDetail(BaseModel):
    # A URI identifying the error *category* (stable, dereferenceable-in-theory).
    type: str = "about:blank"
    # Short, human-readable summary of the category (e.g. "Not Found").
    title: str
    # The HTTP status code, duplicated in the body per the RFC.
    status: int
    # Human-readable detail specific to THIS occurrence.
    detail: Optional[str] = None
    # The path that produced the error.
    instance: Optional[str] = None
    # Validation errors (422) attach the field-level breakdown here.
    errors: Optional[Any] = None
