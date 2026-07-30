"""Global exception handlers that render every error as problem+json.

One `register_exception_handlers(app)` call wires:
- HTTPException            -> problem+json with the raised status/detail
- RequestValidationError   -> 422 problem+json with the field-level breakdown
- Exception (catch-all)    -> 500 problem+json, logged with the request id

WHY-THIS-WAY: FastAPI's defaults return `{"detail": ...}` with a plain
`application/json` content type, and validation errors return a bare list.
Normalizing them here means the ENTIRE surface speaks one error dialect —
media type `application/problem+json` included, so clients can content-negotiate.
"""
from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ProblemDetail

logger = logging.getLogger("app")

_PROBLEM_MEDIA_TYPE = "application/problem+json"


def _phrase(code: int) -> str:
    try:
        return HTTPStatus(code).phrase
    except ValueError:
        return "Error"


def _problem_response(problem: ProblemDetail) -> JSONResponse:
    # jsonable_encoder coerces anything json.dumps can't take directly — most
    # importantly the raw request body that RequestValidationError stashes as
    # `bytes` in each error's `input` field (bytes -> str). Without this a
    # clean 422 crashes the handler and surfaces as a confusing 500.
    return JSONResponse(
        status_code=problem.status,
        content=jsonable_encoder(problem.model_dump(exclude_none=True)),
        media_type=_PROBLEM_MEDIA_TYPE,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        problem = ProblemDetail(
            type=f"https://quillandcode.dev/errors/{exc.status_code}",
            title=_phrase(exc.status_code),
            status=exc.status_code,
            detail=exc.detail if isinstance(exc.detail, str) else None,
            instance=request.url.path,
        )
        response = _problem_response(problem)
        # Preserve auth challenge headers (e.g. WWW-Authenticate) if set.
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        problem = ProblemDetail(
            type="https://quillandcode.dev/errors/validation",
            title="Unprocessable Entity",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more fields failed validation.",
            instance=request.url.path,
            errors=exc.errors(),
        )
        return _problem_response(problem)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # The DB log handler + Sentry capture the full traceback; the client
        # gets a generic message with the request id for correlation.
        logger.exception(
            "Unhandled 500",
            extra={
                "request_context": {
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else "unknown",
                }
            },
        )
        problem = ProblemDetail(
            type="https://quillandcode.dev/errors/500",
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. The team has been notified.",
            instance=request.url.path,
        )
        return _problem_response(problem)
