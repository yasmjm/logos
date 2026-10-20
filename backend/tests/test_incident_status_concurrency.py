"""Real concurrency: two requests, separate connections, committed data.

Unlike the other API tests (one rolled-back transaction per test), each request here
gets its own session and commits for real, so the data is created committed and
removed explicitly at the end.
"""

import threading
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    Analyst,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
    Severity,
)
from tests.factories import auth_headers
from tests.settings import TEST_SETTINGS

THREADS = 2


@pytest.fixture
def committed(db_engine: Engine) -> Generator[tuple[sessionmaker[Session], list, Incident]]:
    make_session = sessionmaker(bind=db_engine, expire_on_commit=False)
    suffix = uuid.uuid4().hex[:8]
    analysts = [
        Analyst(
            id=uuid.uuid4(),
            name=f"Analyst {i}",
            username=f"race-{i}-{suffix}",
            password_hash=hash_password("x"),
        )
        for i in range(THREADS)
    ]
    now = datetime.now(UTC)
    incident = Incident(
        id=uuid.uuid4(),
        description="Pneu estourado no eixo traseiro.",
        category=IncidentCategory.MECHANICAL_FAILURE,
        severity=Severity.LOW,
        truck_code="TRK-RACE",
        highway="BR-116",
        km=Decimal("1.0"),
        location_note="Teste de concorrência",
        created_at=now,
        updated_at=now,
    )
    with make_session() as session, session.begin():
        session.add_all([*analysts, incident])

    def per_request_session() -> Generator[Session]:
        with make_session() as session:
            yield session

    app.dependency_overrides[get_db] = per_request_session
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    try:
        yield make_session, analysts, incident
    finally:
        app.dependency_overrides.clear()
        # Test data only: the audit trail of real incidents is never deleted.
        with make_session() as session, session.begin():
            session.execute(delete(IncidentEvent).where(IncidentEvent.incident_id == incident.id))
            session.execute(delete(Incident).where(Incident.id == incident.id))
            session.execute(delete(Analyst).where(Analyst.id.in_([a.id for a in analysts])))


def test_two_analysts_taking_the_same_incident_at_once(committed) -> None:
    make_session, analysts, incident = committed
    barrier = threading.Barrier(THREADS)
    results: dict[uuid.UUID, int] = {}
    errors: list[BaseException] = []

    def take(analyst: Analyst) -> None:
        try:
            client = TestClient(app)
            barrier.wait(timeout=5)  # release both requests at the same moment
            response = client.patch(
                f"/incidents/{incident.id}/status",
                json={"status": "investigating", "version": 1},
                headers=auth_headers(analyst),
            )
            results[analyst.id] = response.status_code
        except BaseException as exc:  # surface thread failures in the test
            errors.append(exc)

    threads = [threading.Thread(target=take, args=(a,)) for a in analysts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert sorted(results.values()) == [200, 409]

    winner = next(analyst_id for analyst_id, code in results.items() if code == 200)
    with make_session() as session:
        row = session.get(Incident, incident.id)
        events = session.scalars(
            select(IncidentEvent).where(
                IncidentEvent.incident_id == incident.id,
                IncidentEvent.event_type == IncidentEventType.STATUS_CHANGED,
            )
        ).all()
    assert row.status is IncidentStatus.INVESTIGATING
    assert row.version == 2
    assert row.assigned_to == winner
    assert len(events) == 1
    assert events[0].analyst_id == winner
