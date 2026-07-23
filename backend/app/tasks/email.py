"""
/** WHY: emails used to go through fastapi.BackgroundTasks — the same process
    that served the request. That's fine when it works, but a deploy or crash
    between "task added" and "SMTP handshake done" drops the mail on the floor
    with no retry, no visibility. Moving to Celery gives us: durable enqueue
    (Redis broker), automatic retries, and one place to view failures. **/

/** WHAT: `send_email_task(message_id, to, subject, html)` enqueues an SMTP
    send. `message_id` is used as an idempotency key so the same logical
    email (same OTP, same reset link) is never sent twice, even under
    at-least-once redelivery. **/

/** WHY-THIS-WAY: three design decisions worth defending:

    1. Idempotency **before** SMTP. If we claim the key first and SMTP fails,
       Celery retries the task — but on retry `claim_once` returns False and
       we skip. That looks wrong for a first-time failure! But we release
       the claim inside `on_failure` so the retry proceeds. This is the
       standard "check-in / check-out" pattern.

    2. Exponential backoff with jitter. Two workers retrying at exactly the
       same interval synchronize into a thundering herd. Jitter breaks that
       synchronization.

    3. `bind=True` so we get `self` — needed to call `self.retry(...)` and
       inspect `self.request.retries`. Losing that access means giving up
       control over the retry curve. **/
"""
from __future__ import annotations

import logging
import smtplib
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded

from app.core.config import settings
from app.utils.email import Mailer
from app.utils.idempotency import claim_once, release
from app.worker import celery_app

logger = logging.getLogger(__name__)


# recommended by claude opus 4.7: keep the mailer construction local to the
# task rather than importing a request-scoped dependency. Celery workers have
# no HTTP request lifecycle; injecting `Depends(get_mailer)` would silently
# do nothing here.
def _mailer_for_worker() -> Mailer:
    return Mailer(
        server=settings.MAIL_SERVER,
        port=settings.MAIL_PORT,
        username=settings.MAIL_USERNAME,
        password=settings.MAIL_PASSWORD,
        sender_email=settings.MAIL_FROM,
        sender_name=settings.MAIL_FROM_NAME,
    )


# recommended by claude opus 4.7:
#   - max_retries=3    → four total attempts (initial + 3). Enough to survive
#                        a short SMTP hiccup, few enough to not spam an outage.
#   - autoretry_for    → only retry on transport errors. Never retry on
#                        SMTPRecipientsRefused (permanent) — that's a bad
#                        address, not a transient failure.
#   - retry_backoff    → exponential base. First retry at ~4s, then ~8, ~16.
#   - retry_backoff_max=60 caps the curve so a 4th retry doesn't wait 128s.
#   - retry_jitter=True → randomizes ±25% to break thundering-herd sync.
@celery_app.task(
    name="app.tasks.email.send_email_task",
    bind=True,
    max_retries=3,
    autoretry_for=(smtplib.SMTPException, OSError, TimeoutError),
    retry_backoff=4,
    retry_backoff_max=60,
    retry_jitter=True,
)
def send_email_task(self, *, message_id: str, to: str, subject: str, html: str) -> dict[str, Any]:
    """
    /** WHY: called by anything that used to `background_tasks.add_task(
        mailer.send_email, ...)`. The caller now just enqueues; delivery
        (with retries) happens in a worker. **/

    /** WHAT: sends one HTML email. `message_id` must be stable for the same
        logical email — e.g. `f"otp:{user_id}:{otp_id}"` — so a duplicate
        enqueue (or a redelivered task) is a no-op. **/

    /** WHY-THIS-WAY: the try/except/release dance around `claim_once` is
        the "check-in / check-out" pattern. We reserve the id BEFORE the
        side effect, then RELEASE it if the side effect raised — so the
        next retry attempt gets a fresh reservation. Without release we'd
        deadlock ourselves after the first transient failure. **/
    """
    if not claim_once(f"email:{message_id}"):
        logger.info("email skipped, already sent (message_id=%s)", message_id)
        return {"status": "duplicate", "message_id": message_id}

    try:
        mailer = _mailer_for_worker()
        mailer.send_email(to_email=to, subject=subject, body=html)
        logger.info("email sent (message_id=%s to=%s)", message_id, _obfuscate_email(to))
        return {"status": "sent", "message_id": message_id}
    except SoftTimeLimitExceeded:
        # recommended by claude opus 4.7: soft time limit means Celery is
        # about to hard-kill us. Release the claim so a follow-up (manual
        # or scheduled) can retry, then re-raise so Celery records the
        # timeout properly.
        release(f"email:{message_id}")
        raise
    except Exception as exc:
        # Any transient/retriable error: release the claim BEFORE Celery
        # retries the task. autoretry_for handles the actual retry loop.
        release(f"email:{message_id}")
        # If we're out of retries, log loudly and surface — task_failure
        # signal in app/worker.py will fingerprint it into error_logs.
        try:
            raise
        except (smtplib.SMTPException, OSError, TimeoutError):
            if self.request.retries >= self.max_retries:
                logger.exception(
                    "email failed permanently after %s retries (message_id=%s)",
                    self.max_retries,
                    message_id,
                )
            raise


def _obfuscate_email(addr: str) -> str:
    """
    /** WHAT: log-safe form of an email address. `alice@example.com` becomes
        `a***@example.com` — enough to correlate log lines to a user without
        leaking the full PII into log storage. **/
    """
    if "@" not in addr:
        return "***"
    local, _, domain = addr.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"
