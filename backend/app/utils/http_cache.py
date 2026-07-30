"""HTTP conditional-request helpers: ETag + revalidation for read endpoints.

WHY: the read surface (story detail, list, search) sent full bodies on every
request with no caching headers at all. ETag + `If-None-Match` lets a client
(or a CDN) revalidate cheaply — a repeat request that hasn't changed comes back
as an empty `304 Not Modified` instead of re-sending the whole payload.

WHY-THIS-WAY: the responses vary per viewer (like/bookmark flags), so the
cache directive is `private, no-cache` (a.k.a. must-revalidate with max-age=0):
shared caches must not reuse one user's body for another, but conditional
revalidation is still allowed and cheap. The ETag is a deterministic hash of the
serialized model, so identical logical content always yields the same validator
— which is exactly what makes the 304 round-trip work.
"""
from __future__ import annotations

import hashlib

from fastapi import Request, Response
from pydantic import BaseModel

# Vary per-user, so never let a shared cache reuse a body — but DO allow the
# client to revalidate via If-None-Match on every request.
CACHE_CONTROL = "private, no-cache"


def make_etag(payload: bytes) -> str:
    """A strong ETag: quoted hex digest of the response bytes."""
    return '"' + hashlib.md5(payload).hexdigest() + '"'


def conditional_model_response(request: Request, response: Response, model: BaseModel):
    """Attach an ETag + revalidation headers to `model`, or short-circuit to a
    bodyless 304 if the caller's `If-None-Match` already matches.

    Returns either the model (FastAPI serializes it via response_model) or a
    bare 304 Response. The ETag is computed from the model's canonical JSON, so
    it's stable across identical responses regardless of the eventual wire bytes.
    """
    etag = make_etag(model.model_dump_json().encode())

    if request.headers.get("if-none-match") == etag:
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": CACHE_CONTROL},
        )

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CACHE_CONTROL
    return model
