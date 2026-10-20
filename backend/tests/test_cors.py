import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app

ALLOWED = "https://logos.example.com"


@pytest.fixture
def cors_client() -> TestClient:
    settings = Settings(
        _env_file=None,
        frontend_origins=f"http://localhost:5173, {ALLOWED}/",
        jwt_secret="test-jwt-secret-with-at-least-32-characters",
    )
    return TestClient(create_app(settings))


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/incidents",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )


@pytest.mark.parametrize("origin", ["http://localhost:5173", ALLOWED])
def test_preflight_from_allowed_origin(cors_client: TestClient, origin: str) -> None:
    response = _preflight(cors_client, origin)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers


def test_preflight_from_other_origin_is_refused(cors_client: TestClient) -> None:
    response = _preflight(cors_client, "https://evil.example.com")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_from_allowed_origin_exposes_headers(cors_client: TestClient) -> None:
    response = cors_client.get("/health", headers={"Origin": ALLOWED})

    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "location" in response.headers["access-control-expose-headers"].lower()
    assert "retry-after" in response.headers["access-control-expose-headers"].lower()


def test_simple_request_from_other_origin_gets_no_cors_headers(cors_client: TestClient) -> None:
    response = cors_client.get("/health", headers={"Origin": "https://evil.example.com"})

    assert response.status_code == 200  # the browser blocks it, not the server
    assert "access-control-allow-origin" not in response.headers


def test_default_origin_is_vite_dev_server() -> None:
    assert Settings(_env_file=None).frontend_origin_list == ["http://localhost:5173"]


@pytest.mark.parametrize("origins", ["*", "http://localhost:5173,*"])
def test_wildcard_origin_is_rejected(origins: str) -> None:
    with pytest.raises(ValidationError, match="never '\\*'"):
        Settings(_env_file=None, frontend_origins=origins)
