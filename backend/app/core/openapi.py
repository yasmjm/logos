from typing import Any

from fastapi import FastAPI

from app.core.errors import PROBLEM_JSON
from app.schemas.problem import ProblemDetail, ValidationProblemDetail

_PROBLEM_REFS = {
    f"#/components/schemas/{model.__name__}" for model in (ProblemDetail, ValidationProblemDetail)
}


def use_problem_json_in_openapi(app: FastAPI) -> None:
    """Document problem responses under application/problem+json, as the API sends them.

    FastAPI always places a response `model` under application/json, so the generated
    schema is post-processed once and cached.
    """
    default_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = default_openapi()
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                for response in operation.get("responses", {}).values():
                    content = response.get("content", {})
                    json_body = content.get("application/json")
                    if json_body and json_body.get("schema", {}).get("$ref") in _PROBLEM_REFS:
                        content[PROBLEM_JSON] = content.pop("application/json")
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
