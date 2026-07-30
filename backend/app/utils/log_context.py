"""Request-scoped log context.

WHY: a request-id set on `request.state` is only reachable where you have the
Request object. Logs emitted deep in a service function — or inside a Celery
task — can't see it. A `contextvars.ContextVar` carries the id implicitly down
the call stack (and across `await` boundaries) so every log line for a request
can be correlated without threading the id through every function signature.

WHAT:
- `request_id_var` — the ContextVar holding the current request/task id.
- `set_request_id()` / `get_request_id()` — bind and read it.
- `bind_request_id()` — context manager that sets and restores (for tasks).
- `RequestIdLogFilter` — a logging.Filter that stamps `record.request_id` onto
  every record so formatters/handlers can emit it uniformly.
"""
from __future__ import annotations

import contextlib
import contextvars
import uuid
from typing import Iterator, Optional
import logging

# "-" is the sentinel for "no request in scope" (e.g. a startup log line).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def set_request_id(request_id: Optional[str] = None) -> str:
    """Bind a request id to the current context, generating one if absent."""
    rid = request_id or uuid.uuid4().hex
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    return request_id_var.get()


@contextlib.contextmanager
def bind_request_id(request_id: Optional[str] = None) -> Iterator[str]:
    """Set the request id for the duration of a block, then restore it.

    Used by Celery tasks: `with bind_request_id(rid): ...` so a task's logs
    carry the id of the request that enqueued it (passed through task kwargs).
    """
    token = request_id_var.set(request_id or uuid.uuid4().hex)
    try:
        yield request_id_var.get()
    finally:
        request_id_var.reset(token)


class RequestIdLogFilter(logging.Filter):
    """Attach the current request id to every log record.

    A filter (not a formatter) so it applies uniformly across every handler —
    the JSON formatter, the stderr handler, and the DB handler all see it.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Don't clobber an explicit request_id already set via `extra=`.
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True
