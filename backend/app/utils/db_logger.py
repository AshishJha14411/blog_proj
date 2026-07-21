# app/utils/db_logger.py
import hashlib
import logging
import threading
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.error_logs import ErrorLog  # ensure this model/table exists

# ErrorLog.message is String(255) — respect the column length or the insert
# itself fails on Postgres (which was silently breaking every DB error log).
_MESSAGE_MAX = 255


class DatabaseLogHandler(logging.Handler):
    def __init__(self, level=logging.ERROR):
        super().__init__(level=level)
        self._local = threading.local()

    def emit(self, record: logging.LogRecord):
        # re-entrancy guard
        if getattr(self._local, "in_emit", False):
            return
        self._local.in_emit = True
        try:
            # ignore noisy libs
            if record.name.startswith("sqlalchemy"):
                return

            # message — truncated to the DB column width, no ellipsis so the hash stays stable
            raw_msg = record.getMessage()
            msg = raw_msg[:_MESSAGE_MAX]

            # traceback
            tb = ""
            if record.exc_info:
                tb = logging.Formatter().formatException(record.exc_info)
                if len(tb) > 8000:
                    tb = tb[:8000] + "…"

            # context (ensure JSON-serializable; your Pii filter will scrub)
            ctx = getattr(record, "request_context", None)
            if ctx and not isinstance(ctx, dict):
                try:
                    ctx = dict(ctx)
                except Exception:
                    ctx = {"_repr": str(ctx)}

            # Fingerprint identical errors together (Sentry-style aggregation)
            # so error_hash uniqueness holds and we can increment `count` instead.
            error_hash = hashlib.sha256(
                f"{record.levelname}|{record.name}|{raw_msg}".encode("utf-8")
            ).hexdigest()

            db: Session = SessionLocal()
            try:
                existing = (
                    db.query(ErrorLog)
                    .filter(ErrorLog.error_hash == error_hash)
                    .first()
                )
                if existing:
                    existing.count = (existing.count or 0) + 1
                else:
                    db.add(
                        ErrorLog(
                            level=record.levelname,
                            message=msg,
                            traceback=tb,
                            request_context=ctx,
                            error_hash=error_hash,
                        )
                    )
                db.commit()
            except Exception:
                # Rollback and swallow — a unique-race between workers falls
                # here harmlessly; anything else can't recurse via logging.
                db.rollback()
            finally:
                db.close()
        finally:
            self._local.in_emit = False

class PiiScrubbingFilter(logging.Filter):
    SENSITIVE = {"authorization", "cookie", "set-cookie", "x-api-key"}

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = getattr(record, "request_context", None)
        if isinstance(ctx, dict) and "headers" in ctx:
            headers = {}
            for k, v in ctx["headers"].items():
                headers[k] = "[REDACTED]" if k.lower() in self.SENSITIVE else str(v)
            ctx["headers"] = headers
            record.request_context = ctx
        return True
