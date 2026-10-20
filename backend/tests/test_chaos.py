import random
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.chaos import CHAOS_TTL, ChaosController
from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app
from app.models import Analyst
from tests.factories import auth_headers, make_incident
from tests.settings import TEST_SETTINGS

PROBLEM_JSON = "application/problem+json"


@pytest.fixture
def chaos_app(db: Session) -> FastAPI:
    app = create_app(TEST_SETTINGS.model_copy(update={"chaos_enabled": True}))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    return app


@pytest.fixture
def chaos(chaos_app: FastAPI) -> ChaosController:
    return chaos_app.state.chaos


@pytest.fixture
def api(chaos_app: FastAPI, current_analyst: Analyst) -> TestClient:
    client = TestClient(chaos_app)
    client.headers.update(auth_headers(current_analyst))
    return client


def _put(api: TestClient, latency_ms: int = 0, failure_rate: float = 0):
    return api.put("/chaos", json={"latency_ms": latency_ms, "failure_rate": failure_rate})


# --- configuration --------------------------------------------------------------------


def test_put_activates_chaos_with_expiry(api: TestClient) -> None:
    before = datetime.now(UTC)

    body = _put(api, latency_ms=300, failure_rate=0.25).json()

    assert body["active"] is True
    assert (body["latency_ms"], body["failure_rate"]) == (300, 0.25)
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert before + CHAOS_TTL <= expires_at <= datetime.now(UTC) + CHAOS_TTL
    assert api.get("/chaos").json() == body


def test_zeros_turn_chaos_off_immediately(api: TestClient) -> None:
    _put(api, failure_rate=1)

    body = _put(api).json()

    assert body == {"latency_ms": 0, "failure_rate": 0.0, "active": False, "expires_at": None}


@pytest.mark.parametrize(
    "config",
    [
        {"latency_ms": -1, "failure_rate": 0},
        {"latency_ms": 5001, "failure_rate": 0},
        {"latency_ms": 0, "failure_rate": 1.5},
        {"latency_ms": 0, "failure_rate": -0.1},
        {"latency_ms": 0},
        {"latency_ms": 0, "failure_rate": 0, "extra": 1},
    ],
)
def test_invalid_config_returns_422(api: TestClient, config: dict) -> None:
    assert api.put("/chaos", json=config).status_code == 422


def test_chaos_requires_authentication(chaos_app: FastAPI) -> None:
    anonymous = TestClient(chaos_app)

    assert anonymous.get("/chaos").status_code == 401
    assert anonymous.put("/chaos", json={"latency_ms": 0, "failure_rate": 1}).status_code == 401


def test_chaos_routes_are_404_when_disabled(client: TestClient) -> None:
    assert client.get("/chaos").status_code == 404
    assert client.put("/chaos", json={"latency_ms": 0, "failure_rate": 1}).status_code == 404


# --- injection ------------------------------------------------------------------------


def test_failure_rate_one_answers_503_on_incidents(api: TestClient) -> None:
    _put(api, failure_rate=1)

    response = api.get("/incidents", headers={"X-Request-ID": "chaos-1"})

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["retry-after"] == "1"
    assert response.headers["x-request-id"] == "chaos-1"
    body = response.json()
    assert "Chaos mode" in body["detail"]
    assert body["request_id"] == "chaos-1"


def test_failure_rate_is_a_proportion(api: TestClient, chaos: ChaosController) -> None:
    chaos.rng = random.Random(7)
    _put(api, failure_rate=0.3)

    statuses = [api.get("/incidents/summary").status_code for _ in range(200)]

    failed = statuses.count(503) / len(statuses)
    assert set(statuses) == {200, 503}
    assert 0.2 < failed < 0.4


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/health"), ("GET", "/ready"), ("GET", "/auth/me"), ("GET", "/chaos")],
)
def test_chaos_never_touches_other_routes(api: TestClient, method: str, path: str) -> None:
    _put(api, latency_ms=0, failure_rate=1)

    assert api.request(method, path).status_code == 200


def test_cors_preflight_is_not_affected(api: TestClient) -> None:
    _put(api, failure_rate=1)

    response = api.options(
        "/incidents",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200


def test_simulated_503_keeps_cors_headers(api: TestClient) -> None:
    _put(api, failure_rate=1)

    response = api.get("/incidents", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_latency_is_injected(api: TestClient, db: Session) -> None:
    make_incident(db)
    _put(api, latency_ms=300, failure_rate=0)

    started = time.perf_counter()
    response = api.get("/incidents")
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed >= 0.3


def test_latency_does_not_apply_to_health(api: TestClient) -> None:
    _put(api, latency_ms=1000, failure_rate=0)

    started = time.perf_counter()
    api.get("/health")

    assert time.perf_counter() - started < 0.5


# --- expiry ---------------------------------------------------------------------------


def test_chaos_turns_itself_off_after_three_minutes(
    api: TestClient, chaos: ChaosController
) -> None:
    now = [datetime(2026, 10, 20, 12, 0, tzinfo=UTC)]
    chaos.clock = lambda: now[0]
    _put(api, failure_rate=1)

    now[0] += CHAOS_TTL - timedelta(seconds=1)
    assert api.get("/incidents").status_code == 503

    now[0] += timedelta(seconds=1)
    assert api.get("/incidents").status_code == 200
    assert api.get("/chaos").json()["active"] is False


def test_each_put_renews_the_deadline(api: TestClient, chaos: ChaosController) -> None:
    now = [datetime(2026, 10, 20, 12, 0, tzinfo=UTC)]
    chaos.clock = lambda: now[0]
    first = _put(api, failure_rate=1).json()["expires_at"]

    now[0] += timedelta(minutes=2)
    second = _put(api, failure_rate=1).json()["expires_at"]

    assert datetime.fromisoformat(second) - datetime.fromisoformat(first) == timedelta(minutes=2)
