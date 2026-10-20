"""Reusable OpenAPI error responses (all rendered as application/problem+json)."""

from typing import Any

from app.schemas.problem import ProblemDetail, ValidationProblemDetail

_RESPONSES: dict[int, dict[str, Any]] = {
    401: {"model": ProblemDetail, "description": "Missing or invalid credentials."},
    404: {"model": ProblemDetail, "description": "Resource not found."},
    422: {"model": ValidationProblemDetail, "description": "Invalid request parameters."},
    500: {"model": ProblemDetail, "description": "Unexpected server error."},
}


def problem_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {code: _RESPONSES[code] for code in status_codes}
