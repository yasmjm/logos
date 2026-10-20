import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.observability import JsonFormatter
from app.main import create_app
from tests.settings import TEST_SETTINGS


def _access_records(caplog: pytest.LogCaptureFixture) -> list[dict]:
    return [r.fields for r in caplog.records if r.name == "logos.access"]


def test_request_id_is_generated_and_returned(anon_client: TestClient) -> None:
    response = anon_client.get("/health")

    request_id = response.headers["x-request-id"]
    assert len(request_id) == 32
    assert request_id != anon_client.get("/health").headers["x-request-id"]


def test_incoming_request_id_is_echoed(anon_client: TestClient) -> None:
    response = anon_client.get("/health", headers={"X-Request-ID": "frontend-abc.123"})

    assert response.headers["x-request-id"] == "frontend-abc.123"


@pytest.mark.parametrize("bad", ["has spaces", "x" * 129, "<script>"])
def test_unsafe_incoming_request_id_is_replaced(anon_client: TestClient, bad: str) -> None:
    response = anon_client.get("/health", headers={"X-Request-ID": bad})

    assert response.headers["x-request-id"] != bad
    assert len(response.headers["x-request-id"]) == 32


def test_error_responses_also_carry_request_id(client: TestClient) -> None:
    response = client.get("/incidents/not-a-uuid")

    assert response.status_code == 422
    assert response.headers["x-request-id"]


def test_one_structured_log_line_per_request(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="logos.access"):
        response = client.get(
            "/incidents/00000000-0000-0000-0000-000000000000",
            headers={"X-Request-ID": "req-42"},
        )

    [entry] = _access_records(caplog)
    assert entry["request_id"] == "req-42"
    assert entry["method"] == "GET"
    assert entry["route"] == "/incidents/{incident_id}"  # template, not the raw id
    assert entry["status"] == response.status_code == 404
    assert isinstance(entry["duration_ms"], float)


def test_json_formatter_outputs_one_json_object() -> None:
    record = logging.LogRecord("logos.access", logging.INFO, __file__, 1, "request", None, None)
    record.fields = {"request_id": "abc", "status": 200}

    line = json.loads(JsonFormatter().format(record))

    assert line["message"] == "request"
    assert line["request_id"] == "abc"
    assert line["status"] == 200


def test_unhandled_error_returns_500_with_request_id(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(TEST_SETTINGS)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    with caplog.at_level(logging.INFO):
        response = TestClient(app, raise_server_exceptions=False).get(
            "/boom", headers={"X-Request-ID": "trace-500"}
        )

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"] == "trace-500"
    body = response.json()
    assert body["request_id"] == "trace-500"
    assert "secret" not in response.text
    assert _access_records(caplog)[0]["status"] == 500
