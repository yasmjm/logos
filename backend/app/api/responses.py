"""Reusable OpenAPI error responses (all rendered as application/problem+json)."""

from typing import Any

from app.schemas.problem import (
    ConflictProblemDetail,
    NotResponsibleProblemDetail,
    ProblemDetail,
    ValidationProblemDetail,
)

_RESPONSES: dict[int, dict[str, Any]] = {
    401: {"model": ProblemDetail, "description": "Missing or invalid credentials."},
    403: {
        "model": NotResponsibleProblemDetail,
        "description": "Only the analyst responsible for the incident can do this.",
    },
    404: {"model": ProblemDetail, "description": "Resource not found."},
    409: {
        "model": ConflictProblemDetail,
        "description": "Version is outdated; `current` holds the incident as it is now.",
    },
    422: {"model": ValidationProblemDetail, "description": "Invalid request parameters."},
    429: {
        "model": ProblemDetail,
        "description": "Rate limit exceeded; wait for the Retry-After header (seconds).",
        "headers": {
            "Retry-After": {"description": "Seconds to wait.", "schema": {"type": "integer"}}
        },
    },
    500: {"model": ProblemDetail, "description": "Unexpected server error."},
}


def problem_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {code: _RESPONSES[code] for code in status_codes}
