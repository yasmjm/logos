"""Global error handlers that render every error as RFC 9457 problem+json."""

import logging
from decimal import Decimal
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import current_request_id

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"


def problem_response(status: int, detail: str, **extensions: Any) -> JSONResponse:
    body = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        **extensions,
    }
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


_PREVIEW_LENGTH = 50


def _preview(value: str | int | float | Decimal) -> str:
    """Echo the rejected value, truncated so huge inputs do not bloat the response."""
    text = repr(str(value)) if isinstance(value, Decimal) else repr(value)
    return text if len(text) <= _PREVIEW_LENGTH else f"{text[:_PREVIEW_LENGTH]}...'"


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _PREVIEW_LENGTH:
        return value[:_PREVIEW_LENGTH] + "..."
    return value


class ProblemException(Exception):
    """Raise to answer with problem+json carrying extra members (e.g. "current")."""

    def __init__(self, status: int, detail: str, **extensions: Any) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.extensions = extensions


async def _problem_exception_handler(_: Request, exc: ProblemException) -> JSONResponse:
    return problem_response(exc.status, exc.detail, **jsonable_encoder(exc.extensions))


_PYDANTIC_PREFIXES = ("Value error, ", "Assertion failed, ")


def _clean_message(message: str) -> str:
    """Drop Pydantic's "Value error, " prefix from messages raised by our validators."""
    for prefix in _PYDANTIC_PREFIXES:
        if message.startswith(prefix):
            message = message.removeprefix(prefix)
            return message[:1].upper() + message[1:]
    return message


def _describe_location(loc: tuple[int | str, ...]) -> str:
    source, *path = loc
    # Drop list indexes so multi-value filters read as "severity", not "severity.0".
    field = ".".join(str(part) for part in path if not isinstance(part, int)) or str(source)
    if source in ("query", "header", "path", "cookie"):
        return f"{source} parameter '{field}'"
    return f"field '{field}'"


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    response = problem_response(exc.status_code, detail)
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def _validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "location": _describe_location(tuple(err["loc"])),
            "message": _clean_message(err["msg"]),
            "input": _truncate(err.get("input")),
        }
        for err in exc.errors()
    ]
    detail = "; ".join(
        f"Invalid {e['location']}: {e['message']}"
        + (
            f" (got {_preview(e['input'])})"
            if isinstance(e["input"], str | int | float | Decimal)
            else ""
        )
        for e in errors
    )
    # Inputs may be non-JSON types after validators ran (e.g. Decimal), so encode them.
    return problem_response(
        HTTPStatus.UNPROCESSABLE_ENTITY, detail, errors=jsonable_encoder(errors)
    )


def with_request_id(**extensions: Any) -> dict[str, Any]:
    """Adds the request ID (for support) to error bodies such as 500 and 503."""
    request_id = current_request_id()
    return {**extensions, "request_id": request_id} if request_id else extensions


def internal_error_response() -> JSONResponse:
    return problem_response(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "An unexpected error occurred. Please try again.",
        **with_request_id(),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return internal_error_response()


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ProblemException, _problem_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
