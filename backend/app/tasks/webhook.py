"""Celery task that delivers a signed webhook, with retries + health tracking.

WHY a task (not an inline HTTP call): the receiver might be slow or down. Doing
the POST in the request path would make OUR latency hostage to THEIR uptime.
The queue also gives us free retries with backoff.

Delivery contract sent to the receiver:
- Body: canonical JSON `{"event": "...", "data": {...}}` (see serialize_event).
- Header `X-Webhook-Signature: sha256=<hex>` — HMAC of the raw body.
- Header `X-Webhook-Event: <event name>`.
The receiver recomputes the HMAC over the raw body and constant-time compares.
"""
from __future__ import annotations

import logging

import requests

from app.core.database import SessionLocal
from app.models.webhook import WebhookEndpoint
from app.services.webhooks import serialize_event, sign_body
from app.utils.time import utcnow
from app.worker import celery_app

logger = logging.getLogger("app")

# After this many consecutive failures the endpoint is auto-disabled — a dead
# URL shouldn't consume retries forever.
_MAX_CONSECUTIVE_FAILURES = 10
_DELIVERY_TIMEOUT = 10  # seconds


@celery_app.task(
    bind=True,
    name="app.tasks.webhook.deliver_webhook_task",
    max_retries=5,
    autoretry_for=(requests.RequestException,),
    retry_backoff=5,
    retry_backoff_max=300,
    retry_jitter=True,
)
def deliver_webhook_task(self, *, endpoint_id: str, event: str, payload: dict) -> dict:
    db = SessionLocal()
    try:
        endpoint = db.get(WebhookEndpoint, endpoint_id)
        if endpoint is None or not endpoint.active:
            return {"status": "skipped", "endpoint_id": endpoint_id}

        body = serialize_event(event, payload)
        signature = sign_body(endpoint.secret, body)

        try:
            resp = requests.post(
                endpoint.url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event,
                    "X-Webhook-Signature": f"sha256={signature}",
                },
                timeout=_DELIVERY_TIMEOUT,
            )
        except requests.RequestException:
            _record_failure(db, endpoint)
            raise  # autoretry_for handles the backoff/retry

        if 200 <= resp.status_code < 300:
            endpoint.consecutive_failures = 0
            endpoint.updated_at = utcnow()
            db.commit()
            return {"status": "delivered", "endpoint_id": endpoint_id, "code": resp.status_code}

        # Non-2xx: count it, then retry (raise a RequestException-compatible error).
        _record_failure(db, endpoint)
        logger.warning("webhook non-2xx: endpoint=%s code=%s", endpoint_id, resp.status_code)
        raise requests.HTTPError(f"receiver returned {resp.status_code}")
    finally:
        db.close()


def _record_failure(db, endpoint: WebhookEndpoint) -> None:
    endpoint.consecutive_failures = (endpoint.consecutive_failures or 0) + 1
    if endpoint.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        endpoint.active = False
        endpoint.disabled_at = utcnow()
        logger.warning("webhook auto-disabled after %s failures: %s",
                       endpoint.consecutive_failures, endpoint.id)
    endpoint.updated_at = utcnow()
    db.commit()
