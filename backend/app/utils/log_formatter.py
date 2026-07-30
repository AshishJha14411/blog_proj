"""Log formatters.

WHY: on Cloud Run, stdout goes straight to Cloud Logging. Plain-text lines are
un-queryable — you can't filter by request_id or level without regex. Emitting
one JSON object per line makes each field (level, logger, request_id, message,
traceback) a structured, searchable key. In dev we keep a readable single-line
format instead, because a human at a terminal doesn't want to read JSON.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging

# Attributes present on every LogRecord — anything NOT in here is treated as a
# caller-supplied `extra=` field and merged into the JSON output.
_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"request_id", "taskName", "message", "asctime"}


class JsonLogFormatter(logging.Formatter):
    """One compact JSON object per log line, safe for Cloud Logging ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": _dt.datetime.fromtimestamp(record.created, _dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        # Merge structured extras (e.g. request_context) that callers attached.
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = _coerce(value)

        return json.dumps(payload, default=str, ensure_ascii=False)


class HumanLogFormatter(logging.Formatter):
    """Readable single line for local dev, with the request id inline."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


def _coerce(value):
    """Best-effort make a value JSON-serializable; never raise from logging."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)
