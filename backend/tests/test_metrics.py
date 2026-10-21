from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Analyst, IncidentStatus, Severity
from tests.factories import make_analyst, make_incident

S = IncidentStatus
NOW = datetime.now(UTC)


def ago(**delta: float) -> datetime:
    return NOW - timedelta(**delta)


@pytest.fixture
def ana(db: Session) -> Analyst:
    return make_analyst(db, "ana", "Ana Souza")


def _metrics(client: TestClient) -> dict:
    response = client.get("/incidents/metrics")
    assert response.status_code == 200
    return response.json()


def test_empty_window(client: TestClient) -> None:
    assert _metrics(client) == {
        "window_hours": 24,
        "mtta_seconds": None,
        "mtta_count": 0,
        "mttr_seconds": None,
        "mttr_count": 0,
        "escalated_now": 0,
        "sla_breached_now": 0,
    }


def test_mtta_averages_incidents_assumed_in_the_last_24h(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    # Assumed 4 and 8 minutes after creation, both within the window: mean 6 min.
    make_incident(
        db,
        status=S.INVESTIGATING,
        assigned_to=ana.id,
        created_at=ago(hours=2),
        acknowledged_at=ago(hours=2) + timedelta(minutes=4),
    )
    make_incident(
        db,
        status=S.INVESTIGATING,
        assigned_to=ana.id,
        created_at=ago(hours=1),
        acknowledged_at=ago(hours=1) + timedelta(minutes=8),
    )
    # Assumed 30 h ago: outside the window.
    make_incident(
        db,
        status=S.INVESTIGATING,
        assigned_to=ana.id,
        created_at=ago(hours=31),
        acknowledged_at=ago(hours=30),
    )

    metrics = _metrics(client)

    assert metrics["mtta_count"] == 2
    assert metrics["mtta_seconds"] == pytest.approx(6 * 60)


def test_mttr_averages_incidents_resolved_in_the_last_24h(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    make_incident(
        db,
        status=S.CLOSED,
        assigned_to=ana.id,
        created_at=ago(hours=3),
        acknowledged_at=ago(hours=3),
        resolved_at=ago(hours=2),
    )  # 60 min
    make_incident(
        db,
        status=S.INCONCLUSIVE,
        assigned_to=ana.id,
        created_at=ago(hours=5),
        acknowledged_at=ago(hours=5),
        resolved_at=ago(hours=4, minutes=30),
    )  # 30 min
    make_incident(db, status=S.CLOSED, created_at=ago(hours=50), resolved_at=ago(hours=48))
    # Reopened: resolved_at was cleared, so it is not resolved anymore.
    make_incident(db, status=S.OPEN, created_at=ago(hours=2), resolved_at=None)

    metrics = _metrics(client)

    assert metrics["mttr_count"] == 2
    assert metrics["mttr_seconds"] == pytest.approx(45 * 60)


def test_escalated_and_sla_breached_now(client: TestClient, db: Session, ana: Analyst) -> None:
    make_incident(db, severity=Severity.HIGH, created_at=ago(minutes=6))  # escalated + breached
    make_incident(db, severity=Severity.HIGH, created_at=ago(minutes=4))  # within both limits
    make_incident(db, severity=Severity.MEDIUM, created_at=ago(minutes=16))  # breached
    make_incident(db, severity=Severity.MEDIUM, created_at=ago(minutes=14))  # within
    make_incident(db, severity=Severity.LOW, created_at=ago(minutes=31))  # breached
    make_incident(db, severity=Severity.LOW, created_at=ago(minutes=20))  # within
    # Owned (investigating) incidents are not "sem dono", however old.
    make_incident(
        db,
        severity=Severity.HIGH,
        status=S.INVESTIGATING,
        assigned_to=ana.id,
        created_at=ago(hours=1),
        acknowledged_at=ago(minutes=50),
    )

    metrics = _metrics(client)

    assert metrics["escalated_now"] == 1
    assert metrics["sla_breached_now"] == 3


def test_soft_deleted_incidents_are_ignored(client: TestClient, db: Session, ana: Analyst) -> None:
    gone = ago(minutes=1)
    make_incident(db, severity=Severity.HIGH, created_at=ago(minutes=30), deleted_at=gone)
    make_incident(
        db,
        status=S.CLOSED,
        assigned_to=ana.id,
        created_at=ago(hours=2),
        acknowledged_at=ago(hours=2),
        resolved_at=ago(hours=1),
        deleted_at=gone,
    )

    metrics = _metrics(client)

    assert metrics["escalated_now"] == 0
    assert metrics["sla_breached_now"] == 0
    assert metrics["mtta_count"] == 0
    assert metrics["mttr_count"] == 0


def test_metrics_require_authentication(anon_client: TestClient) -> None:
    assert anon_client.get("/incidents/metrics").status_code == 401
