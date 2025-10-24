# app/middleware/logging.py
import time, uuid, logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger_name: str = "app"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
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
