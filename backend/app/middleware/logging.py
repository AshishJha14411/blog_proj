# app/middleware/logging.py
import time, uuid, logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from app.utils.log_context import set_request_id

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger_name: str = "app"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next):
        # Honor an upstream request id (gateway/proxy/client) so a trace can be
        # correlated across services; otherwise mint one.
        incoming = request.headers.get("x-request-id")
        request_id = incoming if incoming else str(uuid.uuid4())
        request.state.request_id = request_id
        # Bind to the contextvar too, so log lines emitted deep in services —
        # where there's no Request object — still carry this id.
        set_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        except Exception:
            # Log the exception here so DB handler always sees it
            self.logger.exception(
                "Unhandled exception in request",
                extra={
                    "request_context": {
                        "method": request.method,
                        "url": str(request.url),
                        "headers": dict(request.headers),
                        "client_ip": request.client.host if request.client else "unknown",
                        "request_id": request_id,
                    }
                },
            )
            raise  # re-raise so your FastAPI exception handler still runs
        finally:
            dur_ms = int((time.perf_counter() - start) * 1000)
            try:
                # nice to have observability headers
                response.headers["x-request-id"] = request_id
                response.headers["x-runtime-ms"] = str(dur_ms)
            except Exception:
                pass
