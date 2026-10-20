from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app
from app.models import Analyst, Incident, IncidentEvent, IncidentEventType, IncidentStatus
from app.seed import TEMPLATES, TOTAL_INCIDENTS
from tests.factories import auth_headers, make_analyst, make_incident
from tests.settings import TEST_SETTINGS


@pytest.fixture
def demo_app(db: Session) -> FastAPI:
    app = create_app(TEST_SETTINGS.model_copy(update={"demo_mode": True}))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    return app


@pytest.fixture
def api(demo_app: FastAPI, current_analyst: Analyst) -> TestClient:
    client = TestClient(demo_app)
    client.headers.update(auth_headers(current_analyst))
    return client


def _count(db: Session, *where) -> int:
    return db.scalar(select(func.count()).select_from(Incident).where(*where))


def _events(db: Session, event_type: IncidentEventType) -> list[IncidentEvent]:
    return list(db.scalars(select(IncidentEvent).where(IncidentEvent.event_type == event_type)))


# --- availability ---------------------------------------------------------------------


def test_demo_routes_are_404_when_demo_mode_is_off(client: TestClient) -> None:
    assert client.post("/demo/reset").status_code == 404
    assert client.post("/demo/simulate").status_code == 404


def test_demo_routes_require_authentication(demo_app: FastAPI) -> None:
    anonymous = TestClient(demo_app)

    assert anonymous.post("/demo/reset").status_code == 401
    assert anonymous.post("/demo/simulate").status_code == 401


# --- reset ----------------------------------------------------------------------------


def test_reset_soft_deletes_old_incidents_and_creates_fresh_demo_set(
    api: TestClient, db: Session, current_analyst: Analyst
) -> None:
    old_open = make_incident(db)
    old_closed = make_incident(db, status=IncidentStatus.CLOSED)
    already_deleted = make_incident(db, deleted_at=datetime.now(UTC) - timedelta(days=1))
    events_before = db.scalar(select(func.count()).select_from(IncidentEvent))

    response = api.post("/demo/reset")

    assert response.status_code == 200
    assert response.json() == {"deleted": 2, "created": TOTAL_INCIDENTS}
    db.expire_all()
    # Old rows are kept, only hidden.
    for incident in (old_open, old_closed):
        assert db.get(Incident, incident.id).deleted_at is not None
    assert db.get(Incident, already_deleted.id).deleted_at < datetime.now(UTC) - timedelta(hours=1)
    assert _count(db, Incident.deleted_at.is_(None)) == TOTAL_INCIDENTS
    # History is never deleted, and the reset itself is audited.
    assert db.scalar(select(func.count()).select_from(IncidentEvent)) > events_before
    deleted = _events(db, IncidentEventType.DELETED)
    assert {e.incident_id for e in deleted} == {old_open.id, old_closed.id}
    assert {e.analyst_id for e in deleted} == {current_analyst.id}
    assert {e.note for e in deleted} == {"Demo reset"}
    assert {e.from_status for e in deleted} == {IncidentStatus.OPEN, IncidentStatus.CLOSED}


def test_reset_dates_are_relative_to_now(api: TestClient, db: Session) -> None:
    api.post("/demo/reset")

    newest, oldest = db.execute(
        select(func.max(Incident.created_at), func.min(Incident.created_at)).where(
            Incident.deleted_at.is_(None)
        )
    ).one()
    now = datetime.now(UTC)
    assert now - timedelta(minutes=5) < newest <= now
    assert oldest >= now - timedelta(hours=6, minutes=1)


def test_reset_keeps_analysts_and_tokens_valid(
    api: TestClient, db: Session, current_analyst: Analyst
) -> None:
    ana = make_analyst(db, "ana", "Ana Souza")

    api.post("/demo/reset")

    db.expire_all()
    assert db.scalars(select(Analyst).where(Analyst.username == "ana")).one().id == ana.id
    assert db.scalar(select(func.count()).select_from(Analyst).where(Analyst.username == "bruno"))
    assert api.get("/incidents?limit=1").status_code == 200  # caller still logged in


def test_reset_is_limited_to_once_per_minute_for_everyone(
    api: TestClient, demo_app: FastAPI, db: Session
) -> None:
    other = TestClient(demo_app, headers=auth_headers(make_analyst(db, "bruno", "Bruno Lima")))

    assert api.post("/demo/reset").status_code == 200
    blocked = other.post("/demo/reset")

    assert blocked.status_code == 429
    assert blocked.headers["content-type"] == "application/problem+json"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60


# --- simulate -------------------------------------------------------------------------


def test_simulate_creates_one_incident_by_default(api: TestClient, db: Session) -> None:
    response = api.post("/demo/simulate")

    assert response.status_code == 201
    [item] = response.json()["items"]
    assert item["status"] == "open"
    assert item["version"] == 1
    assert item["priority_score"] > 0
    created = _events(db, IncidentEventType.CREATED)
    assert [str(e.incident_id) for e in created] == [item["id"]]


def test_simulate_uses_seed_templates_with_coherent_severity(api: TestClient, db: Session) -> None:
    templates = {t.description: t for t in TEMPLATES}

    items = api.post("/demo/simulate", params={"count": 10}).json()["items"]

    assert len(items) == 10
    for item in items:
        template = templates[item["description"]]
        assert (item["category"], item["severity"]) == (
            template.category.value,
            template.severity.value,
        )
    assert len(_events(db, IncidentEventType.CREATED)) == 10


@pytest.mark.parametrize("count", [0, 11, -1])
def test_simulate_count_must_be_between_1_and_10(api: TestClient, count: int) -> None:
    assert api.post("/demo/simulate", params={"count": count}).status_code == 422


def test_simulate_is_limited_per_analyst(api: TestClient, demo_app: FastAPI, db: Session) -> None:
    statuses = [api.post("/demo/simulate").status_code for _ in range(10)]
    blocked = api.post("/demo/simulate")
    other = TestClient(demo_app, headers=auth_headers(make_analyst(db, "bruno", "Bruno Lima")))

    assert statuses == [201] * 10
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers
    assert other.post("/demo/simulate").status_code == 201
