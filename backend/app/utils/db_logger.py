# app/utils/db_logger.py
import logging, threading
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.error_logs import ErrorLog  # ensure this model/table exists

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

            # message
            msg = record.getMessage()
            if len(msg) > 1000:
                msg = msg[:1000] + "…"

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

            db: Session = SessionLocal()
            try:
                error_log = ErrorLog(
                    level=record.levelname,
                    message=msg,
                    traceback=tb,
                    request_context=ctx,
                )
                db.add(error_log)
                db.commit()
            except Exception as e:
                db.rollback()
                # last resort: avoid recursion by NOT logging via logging module here
                print(f"[DB-LOGGING-FAIL] {e} while writing: level={record.levelname} msg={msg!r}")
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
