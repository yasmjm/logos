import logging
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.tokens import ALGORITHM, create_access_token
from app.main import app, create_app
from app.models import Analyst
from app.services import auth as auth_service
from tests.factories import auth_headers, make_analyst, make_incident
from tests.settings import TEST_INGEST_API_KEY, TEST_SETTINGS

PROBLEM_JSON = "application/problem+json"
PASSWORD = "logos123"


@pytest.fixture
def ana(db: Session) -> Analyst:
    return make_analyst(db, "ana", "Ana Souza", password=PASSWORD)


def _login(client: TestClient, username: str, password: str):
    # OAuth2 password flow: form-encoded, as Swagger's Authorize sends it.
    return client.post("/auth/login", data={"username": username, "password": password})


def _token(claims: dict, secret: str = TEST_SETTINGS.jwt_signing_key) -> str:
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


# --- login ----------------------------------------------------------------------------


def test_login_returns_token_and_analyst(anon_client: TestClient, ana: Analyst) -> None:
    response = _login(anon_client, "ana", PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 8 * 60 * 60
    assert body["analyst"] == {"id": str(ana.id), "name": "Ana Souza", "username": "ana"}

    claims = jwt.decode(body["access_token"], TEST_SETTINGS.jwt_signing_key, algorithms=[ALGORITHM])
    assert claims["sub"] == str(ana.id)
    assert claims["exp"] - claims["iat"] == 8 * 60 * 60


def test_token_from_login_authenticates_requests(anon_client: TestClient, ana: Analyst) -> None:
    token = _login(anon_client, "ana", PASSWORD).json()["access_token"]

    response = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "ana"


@pytest.mark.parametrize(
    ("username", "password"), [("ana", "wrong-password"), ("nobody", PASSWORD), ("ANA", PASSWORD)]
)
def test_invalid_credentials_return_same_generic_401(
    anon_client: TestClient, ana: Analyst, username: str, password: str
) -> None:
    response = _login(anon_client, username, password)

    assert response.status_code == 401
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"] == "Invalid username or password."
    assert "access_token" not in response.text


def test_unknown_user_still_runs_password_hash(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    checked: list[str] = []
    real_verify = auth_service.verify_password

    def spy(password: str, password_hash: str) -> bool:
        checked.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(auth_service, "verify_password", spy)

    assert _login(anon_client, "nobody", PASSWORD).status_code == 401
    assert checked == [auth_service.DUMMY_PASSWORD_HASH]


def test_login_requires_both_fields(anon_client: TestClient) -> None:
    assert anon_client.post("/auth/login", data={"username": "ana"}).status_code == 422


def test_me_returns_authenticated_analyst(client: TestClient, current_analyst: Analyst) -> None:
    response = client.get("/auth/me")

    assert response.json() == {
        "id": str(current_analyst.id),
        "name": current_analyst.name,
        "username": current_analyst.username,
    }


# --- protected routes -----------------------------------------------------------------

INCIDENT_ID = "00000000-0000-0000-0000-000000000001"
ANALYST_ROUTES = [
    ("GET", "/auth/me"),
    ("GET", "/incidents"),
    ("GET", "/incidents/summary"),
    ("GET", f"/incidents/{INCIDENT_ID}"),
    ("PATCH", f"/incidents/{INCIDENT_ID}"),
    ("PATCH", f"/incidents/{INCIDENT_ID}/status"),
    ("DELETE", f"/incidents/{INCIDENT_ID}"),
]


@pytest.mark.parametrize(("method", "path"), ANALYST_ROUTES)
def test_analyst_routes_require_token(anon_client: TestClient, method: str, path: str) -> None:
    response = anon_client.request(method, path, json={"version": 1, "status": "open"})

    assert response.status_code == 401
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["www-authenticate"] == "Bearer"
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        _token({"sub": str(uuid.uuid4())}),  # missing exp/iat
        _token(
            {"sub": str(uuid.uuid4()), "iat": 1, "exp": 4102444800},
            secret="another-secret-with-at-least-32-characters!",
        ),
        jwt.encode({"sub": "x", "iat": 1, "exp": 4102444800}, key=None, algorithm="none"),
        _token({"sub": "not-a-uuid", "iat": 1, "exp": 4102444800}),
    ],
    ids=["garbage", "missing-claims", "wrong-signature", "alg-none", "bad-subject"],
)
def test_invalid_token_returns_401(anon_client: TestClient, token: str) -> None:
    response = anon_client.get("/incidents", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token."


def test_expired_token_returns_401(anon_client: TestClient, ana: Analyst) -> None:
    past = datetime.now(UTC) - timedelta(hours=9)
    token = _token({"sub": str(ana.id), "iat": past, "exp": past + timedelta(hours=8)})

    response = anon_client.get("/incidents", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Session expired. Log in again."


def test_token_of_removed_analyst_returns_401(anon_client: TestClient) -> None:
    ghost = Analyst(id=uuid.uuid4(), name="x", username="x", password_hash="x")

    response = anon_client.get("/incidents", headers=auth_headers(ghost))

    assert response.status_code == 401


def test_health_is_public(anon_client: TestClient) -> None:
    assert anon_client.get("/health").status_code == 200


def test_ingestion_still_uses_api_key_not_token(client: TestClient, db: Session) -> None:
    body = {
        "category": "mechanical_failure",
        "severity": "low",
        "description": "Pneu furado no eixo",
        "truck_code": "TRK-1",
    }

    assert client.post("/incidents", json=body).status_code == 401  # token alone is not enough
    created = client.post("/incidents", json=body, headers={"X-API-Key": TEST_INGEST_API_KEY})
    assert created.status_code == 201


def test_events_use_the_token_analyst(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db)

    client.patch(
        f"/incidents/{incident.id}/status",
        json={"status": "investigating", "version": 1},
        headers=auth_headers(ana),
    )

    events = client.get(f"/incidents/{incident.id}").json()["events"]
    assert events[-1]["analyst"]["name"] == "Ana Souza"


# --- OpenAPI --------------------------------------------------------------------------


def test_openapi_uses_oauth2_password_flow() -> None:
    schemes = app.openapi()["components"]["securitySchemes"]

    assert schemes["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "/auth/login"


@pytest.mark.parametrize(("method", "path"), ANALYST_ROUTES)
def test_openapi_documents_401_on_analyst_routes(method: str, path: str) -> None:
    template = path.replace(INCIDENT_ID, "{incident_id}")
    operation = app.openapi()["paths"][template][method.lower()]

    assert "application/problem+json" in operation["responses"]["401"]["content"]
    assert {"OAuth2PasswordBearer": []} in operation["security"]


def test_x_analyst_id_header_is_gone() -> None:
    assert "X-Analyst-Id" not in str(app.openapi())


# --- settings -------------------------------------------------------------------------


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_production_requires_strong_jwt_secret(secret: str | None) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(app_env="production", jwt_secret=secret)


def test_production_accepts_32_character_secret() -> None:
    settings = _settings(app_env="production", jwt_secret="x" * 32)

    assert settings.jwt_signing_key == "x" * 32


def test_development_without_secret_uses_fallback_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = _settings(app_env="development")

    with caplog.at_level(logging.WARNING):
        create_app(settings)

    assert settings.jwt_signing_key
    assert "JWT_SECRET is not set" in caplog.text
    assert create_access_token(uuid.uuid4(), settings)


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_secrets_count_as_not_configured(blank: str) -> None:
    settings = _settings(jwt_secret=blank, ingest_api_key=blank)

    assert settings.jwt_secret is None
    assert settings.ingest_api_key is None
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(app_env="production", jwt_secret=blank)
