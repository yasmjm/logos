from collections.abc import Generator

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_db, session_dependency
from app.core.db_errors import is_statement_timeout, is_transient_connection_error
from app.core.retry import retry_transient
from app.main import app, create_app
from app.services import incident_status
from app.services import incidents as incident_service
from tests.factories import make_incident
from tests.settings import TEST_SETTINGS

PROBLEM_JSON = "application/problem+json"


def _connection_lost() -> OperationalError:
    return OperationalError("SELECT 1", {}, psycopg.OperationalError("connection refused"))


def _statement_timeout() -> OperationalError:
    return OperationalError("SELECT 1", {}, psycopg.errors.QueryCanceled("statement timeout"))


# --- classification and retry ---------------------------------------------------------


def test_error_classification() -> None:
    assert is_transient_connection_error(_connection_lost())
    assert not is_transient_connection_error(_statement_timeout())
    assert is_statement_timeout(_statement_timeout())
    assert not is_transient_connection_error(ValueError("not a db error"))


def test_retry_recovers_from_transient_failures_with_jittered_backoff() -> None:
    calls, waits, rollbacks = [], [], []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise _connection_lost()
        return "ok"

    result = retry_transient(
        flaky, before_retry=lambda: rollbacks.append(1), sleep=waits.append, jitter=lambda: 0.5
    )

    assert result == "ok"
    assert len(calls) == 3
    assert len(rollbacks) == 2
    assert waits == [0.025, 0.05]  # 50% of 50ms, then 50% of 100ms


def test_retry_gives_up_after_three_attempts() -> None:
    calls = []

    def down() -> None:
        calls.append(1)
        raise _connection_lost()

    with pytest.raises(OperationalError):
        retry_transient(down, sleep=lambda _: None)
    assert len(calls) == 3


def test_slow_query_is_not_retried() -> None:
    calls = []

    def slow() -> None:
        calls.append(1)
        raise _statement_timeout()

    with pytest.raises(OperationalError):
        retry_transient(slow, sleep=lambda _: None)
    assert len(calls) == 1


# --- through the API ------------------------------------------------------------------


@pytest.fixture
def database_down(anon_client: TestClient) -> Generator[None, None, None]:
    """The real get_db, but on an engine pointing at a closed port: connections are refused."""
    engine = create_engine(
        "postgresql+psycopg://logos:logos@127.0.0.1:1/logos", connect_args={"connect_timeout": 1}
    )
    app.dependency_overrides[get_db] = session_dependency(sessionmaker(bind=engine))
    yield
    engine.dispose()


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/incidents"), ("GET", "/incidents/summary"), ("GET", "/auth/me")],
)
def test_database_down_returns_503_not_500(
    anon_client: TestClient, database_down: None, method: str, path: str
) -> None:
    response = anon_client.request(
        method, path, headers={"Authorization": "Bearer x", "X-Request-ID": "db-down-1"}
    )

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["retry-after"] == "5"
    body = response.json()
    assert body["title"] == "Service Unavailable"
    assert "temporarily unavailable" in body["detail"]
    assert body["request_id"] == "db-down-1"
    assert "127.0.0.1" not in response.text  # no connection details leak


def test_read_retries_and_recovers_after_transient_failure(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    incident = make_incident(db)
    db.commit()  # survive the rollback that precedes each retry
    real_list = incident_service.list_incidents
    calls = []

    def fails_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise _connection_lost()
        return real_list(*args, **kwargs)

    monkeypatch.setattr(incident_service, "list_incidents", fails_once)

    response = client.get("/incidents")

    assert response.status_code == 200
    assert [i["id"] for i in response.json()["items"]] == [str(incident.id)]
    assert len(calls) == 2


def test_writes_are_not_retried_on_the_server(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    incident = make_incident(db)
    calls = []

    def write_fails(*args, **kwargs) -> None:
        calls.append(1)
        raise _connection_lost()

    monkeypatch.setattr(incident_status, "change_status", write_fails)

    response = client.patch(
        f"/incidents/{incident.id}/status", json={"status": "investigating", "version": 1}
    )

    assert response.status_code == 503
    assert len(calls) == 1


def test_real_statement_timeout_returns_503_without_retry(db: Session) -> None:
    timeout_app = create_app(TEST_SETTINGS)
    calls = []

    @timeout_app.get("/slow")
    def slow() -> None:
        calls.append(1)
        db.execute(text("SET LOCAL statement_timeout = 50"))
        db.execute(text("SELECT pg_sleep(1)"))

    response = TestClient(timeout_app).get("/slow")

    assert response.status_code == 503
    assert "took too long" in response.json()["detail"]
    assert len(calls) == 1


# --- liveness and readiness -----------------------------------------------------------


def test_ready_when_database_answers(anon_client: TestClient) -> None:
    response = anon_client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_when_database_is_down(
    anon_client: TestClient, database_down: None
) -> None:
    response = anon_client.get("/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["retry-after"] == "5"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_health_stays_up_when_database_is_down(
    anon_client: TestClient, database_down: None
) -> None:
    response = anon_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_503_with_retry_after() -> None:
    operation = app.openapi()["paths"]["/ready"]["get"]

    assert "Retry-After" in operation["responses"]["503"]["headers"]
    assert "503" not in app.openapi()["paths"]["/health"]["get"]["responses"]
