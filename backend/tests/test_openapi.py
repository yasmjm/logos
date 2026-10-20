import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.problem import ProblemDetail, ValidationProblemDetail

PROBLEM_JSON = "application/problem+json"


def _responses(path: str) -> dict:
    return app.openapi()["paths"][path]["get"]["responses"]


def _schema_ref(response: dict) -> str:
    return response["content"][PROBLEM_JSON]["schema"]["$ref"].rsplit("/", 1)[-1]


def test_error_responses_are_documented_as_problem_json() -> None:
    detail = _responses("/incidents/{incident_id}")

    assert _schema_ref(detail["404"]) == "ProblemDetail"
    assert _schema_ref(detail["422"]) == "ValidationProblemDetail"
    assert _schema_ref(detail["500"]) == "ServerProblemDetail"
    assert _schema_ref(detail["503"]) == "ServerProblemDetail"
    assert "application/json" not in detail["404"]["content"]


def test_every_operation_documents_500() -> None:
    for operations in app.openapi()["paths"].values():
        for operation in operations.values():
            assert _schema_ref(operation["responses"]["500"]) == "ServerProblemDetail"


def test_fastapi_default_validation_schema_is_not_exposed() -> None:
    assert "HTTPValidationError" not in app.openapi()["components"]["schemas"]


def test_documented_schemas_match_real_error_bodies(client: TestClient) -> None:
    not_found = client.get(f"/incidents/{uuid.uuid4()}")
    invalid = client.get("/incidents", params={"severity": "urgent"})

    ProblemDetail.model_validate(not_found.json(), strict=True)
    ValidationProblemDetail.model_validate(invalid.json(), strict=True)
