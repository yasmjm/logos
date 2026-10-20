import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.rate_limit import RateLimiter
from app.main import app
from tests.factories import make_analyst
from tests.settings import TEST_INGEST_API_KEY

PROBLEM_JSON = "application/problem+json"


def _login(client: TestClient, password: str = "wrong-password"):
    return client.post("/auth/login", data={"username": "ana", "password": password})


# --- login: 5 per minute per IP -------------------------------------------------------


def test_sixth_login_attempt_in_a_minute_returns_429(anon_client: TestClient, db: Session) -> None:
    make_analyst(db, "ana", "Ana Souza", password="logos123")

    statuses = [_login(anon_client).status_code for _ in range(5)]
    blocked = _login(anon_client, password="logos123")  # even the right password

    assert statuses == [401] * 5
    assert blocked.status_code == 429
    assert blocked.headers["content-type"] == PROBLEM_JSON
    retry_after = int(blocked.headers["retry-after"])
    assert 1 <= retry_after <= 60
    assert f"Try again in {retry_after} seconds" in blocked.json()["detail"]


def test_login_limit_is_per_ip(anon_client: TestClient) -> None:
    for _ in range(6):
        _login(anon_client)

    other_ip = TestClient(app, client=("203.0.113.7", 50000))

    assert _login(other_ip).status_code == 401


# --- ingestion: 120 per minute per key ------------------------------------------------


def _ingest(client: TestClient, key: str = TEST_INGEST_API_KEY):
    # Empty body: rejected with 422 after auth and rate limit, so no rows are written.
    return client.post("/incidents", json={}, headers={"X-API-Key": key})


def test_ingestion_over_120_per_minute_returns_429(anon_client: TestClient) -> None:
    statuses = {_ingest(anon_client).status_code for _ in range(120)}
    blocked = _ingest(anon_client)

    assert statuses == {422}
    assert blocked.status_code == 429
    assert blocked.headers["content-type"] == PROBLEM_JSON
    assert int(blocked.headers["retry-after"]) >= 1


def test_requests_with_invalid_key_do_not_consume_the_budget(anon_client: TestClient) -> None:
    for _ in range(130):
        assert _ingest(anon_client, key="wrong").status_code == 401

    assert _ingest(anon_client).status_code == 422


# --- limiter --------------------------------------------------------------------------


def test_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now[0])
    limiter = RateLimiter(limit=2, window_seconds=60)

    assert limiter.hit("k") is None
    now[0] += 30
    assert limiter.hit("k") is None
    assert limiter.hit("k") == 30  # oldest hit leaves the window in 30s
    now[0] += 30
    assert limiter.hit("k") is None  # first hit expired
    assert limiter.hit("other") is None  # keys are independent


def test_openapi_documents_429() -> None:
    paths = app.openapi()["paths"]

    for operation in (paths["/auth/login"]["post"], paths["/incidents"]["post"]):
        response = operation["responses"]["429"]
        assert PROBLEM_JSON in response["content"]
        assert "Retry-After" in response["headers"]
