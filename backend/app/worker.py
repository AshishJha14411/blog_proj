"""
/** WHY: BackgroundTasks runs jobs in the same worker process that served the
    request. If uvicorn dies mid-send (deploy, OOM, SIGTERM) the email is lost
    forever — no retry, no visibility. UPGRADE_PLAN Phase 2 replaces that with
    a real durable queue backed by Redis. **/

/** WHAT: exposes a single Celery `app` object. Every module that wants to
    enqueue work imports it as `from app.worker import celery_app` and calls
    `.send_task(...)` or uses the `@celery_app.task` decorator (see
    app/tasks/*). **/

/** WHY-THIS-WAY: single `app` per process, tasks live in `app.tasks.*` and
    are imported through the `include=` list below so a `celery -A app.worker`
    command discovers every task in one place. **/
"""
from __future__ import annotations

import logging
import ssl
from urllib.parse import urlparse

from celery import Celery
from celery.signals import task_failure

from app.core.config import settings

logger = logging.getLogger(__name__)


# recommended by claude opus 4.7: point broker + backend at the same Redis
# instance for now. In prod you can split them (broker on Upstash, results
# elsewhere) by setting CELERY_BROKER_URL / CELERY_RESULT_BACKEND env vars
# — Celery reads those automatically and they override REDIS_URL.
celery_app = Celery(
    "quill",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email",
        "app.tasks.moderation",
        "app.tasks.support",
        "app.tasks.webhook",
        # future task modules go here; keep the list explicit so imports fire
        # and @task registrations happen at worker start, not lazily.
    ],
)

# WHY: kombu's redis transport raises `ValueError: A rediss:// URL must have
# parameter ssl_cert_reqs...` unless broker_use_ssl is set explicitly — unlike
# plain redis-py (app/core/redis.py), which infers sane TLS defaults from the
# scheme alone. Managed Redis providers (Upstash included) are TLS-only, so
# every prod deploy hits this the moment a task is first enqueued: the row
# already committed to Postgres, then `.delay()` raises and the request 500s.
if urlparse(settings.REDIS_URL).scheme == "rediss":
    _redis_ssl_opts = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    celery_app.conf.update(
        broker_use_ssl=_redis_ssl_opts,
        redis_backend_use_ssl=_redis_ssl_opts,
    )


# ---------------------------------------------------------------------------
# Config — every non-default is here so the choices are auditable in one place.
# ---------------------------------------------------------------------------
celery_app.conf.update(
    # recommended by claude opus 4.7: JSON serialization. Never pickle over a
    # network — pickle deserializes arbitrary classes and is a well-known RCE
    # foot-cannon on shared brokers.
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # recommended by claude opus 4.7: ack AFTER the task finishes, not on
    # dequeue. Combined with `task_reject_on_worker_lost`, a SIGKILL'd worker
    # loses no messages — the broker re-delivers them to the next available
    # worker. Trade-off: at-least-once delivery, which is why every task must
    # be idempotent (see app/utils/idempotency.py + tasks that use it).
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # recommended by claude opus 4.7: prefetch=1 so slow tasks don't hog a
    # worker that could be doing fast ones. Default (4) causes head-of-line
    # blocking when a single 30s LLM job locks four small email jobs behind
    # it.
    worker_prefetch_multiplier=1,

    # recommended by claude opus 4.7: hard time limits so a runaway task
    # (bad regex, LLM stuck) doesn't hold a worker forever. Soft limit fires
    # a SoftTimeLimitExceeded exception so the task can clean up; hard limit
    # SIGKILLs.
    task_soft_time_limit=25,   # seconds
    task_time_limit=30,

    # recommended by claude opus 4.7: keep results for 24h then TTL them out
    # of Redis. Long enough for the frontend to poll status on async jobs
    # (Phase 4 chatbot / LLM generation); short enough that Redis memory
    # doesn't drift up forever.
    result_expires=60 * 60 * 24,

    # recommended by claude opus 4.7: route the special "failed" queue so
    # dead-letter tasks can be inspected separately. If you scale workers
    # later you can dedicate one to `failed` to run alerting hooks.
    task_default_queue="default",
    task_routes={
        "app.tasks.email.*": {"queue": "default"},
        "app.tasks.moderation.*": {"queue": "default"},
        "app.tasks.support.*": {"queue": "default"},
        "app.tasks.webhook.*": {"queue": "default"},
    },

    # recommended by claude opus 4.7: keep task registration explicit; do NOT
    # let Celery auto-discover from an app directory. Discovery makes
    # circular-import bugs mysterious.
    imports=[],
)


# ---------------------------------------------------------------------------
# WORKERLESS MODE (cost decision — see app/core/config.py + docs/adr/001)
# ---------------------------------------------------------------------------
# /** WHY: a polling Celery worker cannot scale to zero on Cloud Run, so it
#     bills for a CPU 24/7. On a personal project that is the whole bill. **/
# /** WHAT: `task_always_eager` runs `.delay()` inline in the caller instead of
#     shipping it to a broker, so NO worker process is needed at all. Every
#     enqueue site commits before enqueueing, so the inline task sees a
#     committed row. **/
# /** WHY-THIS-WAY: `task_eager_propagates=False` is the important half. With
#     it True (the test setting) a failing task would raise straight into the
#     request and 500 a story-publish because the LLM hiccuped. False keeps the
#     failure inside the task: the write already succeeded, the story simply
#     stays `pending` and can be re-published to retry. Degrade, don't explode. **/
if settings.CELERY_TASK_ALWAYS_EAGER:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=False,
    )


# ---------------------------------------------------------------------------
# Failure hook — writes to the same error_logs table used by the DB log
# handler. Keeps every asynchronous failure discoverable without adding
# another sink to check.
# ---------------------------------------------------------------------------
@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **_):
    """
    /** WHY: an unhandled task exception used to vanish into the worker's
        stderr. Now every failure is fingerprinted into `error_logs` via the
        same `logger.exception` path the request handlers use. **/

    /** WHY-THIS-WAY: reuse the DatabaseLogHandler infra (fingerprint +
        upsert-or-increment) so identical Celery + web failures aggregate into
        the same row. **/
    """
    task_name = getattr(sender, "name", "unknown")
    logger.exception(
        "celery task failed: %s (task_id=%s)",
        task_name,
        task_id,
        exc_info=(type(exception), exception, traceback) if exception else None,
        extra={
            "request_context": {
                "kind": "celery_task",
                "task": task_name,
                "task_id": task_id,
                # Args intentionally excluded — they can contain the user's
                # email address / OTP raw code. If you need them for a
                # postmortem, use the transient result backend.
            }
        },
    )
