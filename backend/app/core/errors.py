"""Global error handlers that render every error as RFC 9457 problem+json."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
            "message": err["msg"],
            "input": err.get("input"),
        }
        for err in exc.errors()
    ]
    detail = "; ".join(
        f"Invalid {e['location']}: {e['message']}"
        + (f" (got {e['input']!r})" if isinstance(e["input"], str | int | float) else "")
        for e in errors
    )
    return problem_response(HTTPStatus.UNPROCESSABLE_ENTITY, detail, errors=errors)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return problem_response(
        HTTPStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred. Please try again."
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
