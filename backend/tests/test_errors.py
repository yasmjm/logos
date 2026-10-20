from typing import Annotated

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import Field

from app.core.errors import register_error_handlers


def _app_with_failing_route() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database exploded: secret connection string")

    @app.get("/echo")
    def echo(name: Annotated[str, Field(max_length=3)]) -> None: ...

    return app


def test_unexpected_error_returns_500_problem_without_internals() -> None:
    client = TestClient(_app_with_failing_route(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred. Please try again.",
    }
    assert "secret" not in response.text


def test_unknown_route_returns_404_problem() -> None:
    response = TestClient(_app_with_failing_route()).get("/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Not Found"


def test_long_rejected_input_is_truncated() -> None:
    response = TestClient(_app_with_failing_route()).get("/echo", params={"name": "x" * 500})

    body = response.json()
    assert response.status_code == 422
    assert len(body["detail"]) < 200
    assert body["errors"][0]["input"].endswith("...")
