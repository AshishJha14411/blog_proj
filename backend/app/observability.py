"""Observability wiring: structured logging, Sentry, Prometheus metrics.

Kept in one module so `main.py` reads as three intent-revealing calls
(`setup_logging()`, `init_sentry()`, `instrument_metrics(app)`) instead of a
pile of handler plumbing. Sentry and Prometheus are OPTIONAL — if the package
isn't installed or the config isn't set, the app runs exactly as before. That
keeps local dev dependency-light while prod gets the full treatment.
"""
from __future__ import annotations

import logging

from app.core.config import settings
from app.utils.log_context import RequestIdLogFilter
from app.utils.log_formatter import HumanLogFormatter, JsonLogFormatter

logger = logging.getLogger("app")


def setup_logging() -> None:
    """Configure the app-scoped logger.

    - JSON formatter in prod (queryable in Cloud Logging), human format in dev.
    - RequestIdLogFilter on every handler so each line carries its request id.
    - The DB error handler (fingerprinted ErrorLog) stays for ERROR+ only.
    - Root handlers are stripped so nothing double-logs.
    """
    # Import here to avoid a circular import at module load (db_logger imports
    # the DB session which imports config which... keep it lazy).
    from app.utils.db_logger import DatabaseLogHandler, PiiScrubbingFilter

    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    app_logger.propagate = False
    app_logger.handlers.clear()  # idempotent: safe if setup runs twice (tests)

    request_id_filter = RequestIdLogFilter()
    formatter: logging.Formatter = JsonLogFormatter() if not settings.IS_DEV else HumanLogFormatter()

    # 1) stdout/stderr — the primary sink (Cloud Logging scrapes it).
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(app_logger.level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(request_id_filter)
    app_logger.addHandler(stream_handler)

    # 2) DB error aggregation — ERROR+ only, fingerprinted + PII-scrubbed.
    db_handler = DatabaseLogHandler(level=logging.ERROR)
    db_handler.addFilter(PiiScrubbingFilter())
    db_handler.addFilter(request_id_filter)
    app_logger.addHandler(db_handler)

    # Quiet noisy libraries; keep them off the app logger's DB handler.
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.INFO)

    # Strip root handlers so records don't get emitted twice.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)


def init_sentry() -> None:
    """Initialize Sentry in production only, if DSN + package are available."""
    if settings.IS_DEV or not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry-sdk not installed; skipping Sentry init")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # We already have a PII scrubber on the DB handler; don't let Sentry
        # ship request bodies/headers by default.
        send_default_pii=False,
    )
    logger.info("sentry: initialized for environment=%s", settings.ENVIRONMENT)


def instrument_metrics(app) -> None:
    """Expose Prometheus metrics at /metrics, if the instrumentator is present."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        logger.info("prometheus-fastapi-instrumentator not installed; /metrics disabled")
        return
    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/metrics", "/healthz"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    logger.info("metrics: /metrics endpoint enabled")
