import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analyst, Incident, IncidentEvent, IncidentEventType, IncidentStatus
from tests.factories import make_analyst, make_incident

S = IncidentStatus
EARLIER = datetime.now(UTC) - timedelta(hours=1)


def _patch(
    client: TestClient,
    incident: Incident,
    status: str,
    analyst: Analyst | None,
    *,
    version: int | None = None,
    note: str | None = None,
    **extra: Any,
):
    body: dict[str, Any] = {"status": status, "version": version or incident.version, **extra}
    if note is not None:
        body["note"] = note
    headers = {"X-Analyst-Id": str(analyst.id)} if analyst else {}
    return client.patch(f"/incidents/{incident.id}/status", json=body, headers=headers)


def _reload(db: Session, incident: Incident) -> Incident:
    db.expire_all()
    return db.get(Incident, incident.id)


def _status_events(db: Session, incident: Incident) -> list[IncidentEvent]:
    return list(
        db.scalars(
            select(IncidentEvent).where(
                IncidentEvent.incident_id == incident.id,
                IncidentEvent.event_type == IncidentEventType.STATUS_CHANGED,
            )
        )
    )


@pytest.fixture
def ana(db: Session) -> Analyst:
    return make_analyst(db, "ana", "Ana Souza")


@pytest.fixture
def bruno(db: Session) -> Analyst:
    return make_analyst(db, "bruno", "Bruno Lima")


# --- valid transitions ----------------------------------------------------------------


def test_take_open_incident(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db)

    response = _patch(client, incident, "investigating", ana)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "investigating"
    assert body["version"] == 2
    assert body["assignee"] == {"id": str(ana.id), "name": "Ana Souza"}
    row = _reload(db, incident)
    assert row.assigned_to == ana.id
    assert row.acknowledged_at is not None
    assert row.resolved_at is None
    assert row.updated_at > incident.created_at
    [event] = _status_events(db, incident)
    assert (event.from_status, event.to_status, event.analyst_id) == (
        S.OPEN,
        S.INVESTIGATING,
        ana.id,
    )
    assert body["events"][-1]["to_status"] == "investigating"


def test_take_keeps_first_acknowledged_at(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, acknowledged_at=EARLIER)  # reopened earlier

    _patch(client, incident, "investigating", ana)

    assert _reload(db, incident).acknowledged_at == EARLIER


def test_release_by_responsible(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(
        db, status=S.INVESTIGATING, assigned_to=ana.id, acknowledged_at=EARLIER
    )

    response = _patch(client, incident, "open", ana, note="Passando para o turno da noite.")

    assert response.status_code == 200
    row = _reload(db, incident)
    assert row.status is S.OPEN
    assert row.assigned_to is None
    assert row.acknowledged_at == EARLIER
    assert row.resolved_at is None
    [event] = _status_events(db, incident)
    assert (event.from_status, event.to_status) == (S.INVESTIGATING, S.OPEN)
    assert event.note == "Passando para o turno da noite."


def test_close_by_responsible(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(
        db, status=S.INVESTIGATING, assigned_to=ana.id, acknowledged_at=EARLIER
    )

    response = _patch(client, incident, "closed", ana)

    assert response.status_code == 200
    row = _reload(db, incident)
    assert row.status is S.CLOSED
    assert row.resolved_at is not None
    assert row.assigned_to == ana.id
    assert response.json()["priority_score"] == 10 + 10  # resolved: no aging


def test_inconclusive_with_note(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, status=S.INVESTIGATING, assigned_to=ana.id)

    response = _patch(
        client, incident, "inconclusive", ana, note="  Motorista não atendeu; rastreador offline.  "
    )

    assert response.status_code == 200
    assert _reload(db, incident).resolved_at is not None
    [event] = _status_events(db, incident)
    assert event.to_status is S.INCONCLUSIVE
    assert event.note == "Motorista não atendeu; rastreador offline."


@pytest.mark.parametrize("closed_status", [S.CLOSED, S.INCONCLUSIVE])
def test_any_analyst_can_reopen(
    client: TestClient, db: Session, ana: Analyst, bruno: Analyst, closed_status: IncidentStatus
) -> None:
    incident = make_incident(
        db,
        status=closed_status,
        assigned_to=ana.id,
        acknowledged_at=EARLIER,
        resolved_at=EARLIER + timedelta(minutes=30),
    )

    response = _patch(client, incident, "open", bruno, note="Motorista ligou de novo.")

    assert response.status_code == 200
    row = _reload(db, incident)
    assert row.status is S.OPEN
    assert row.resolved_at is None
    assert row.assigned_to is None
    assert row.acknowledged_at == EARLIER
    [event] = _status_events(db, incident)
    assert (event.from_status, event.to_status, event.analyst_id) == (
        closed_status,
        S.OPEN,
        bruno.id,
    )


# --- invalid transitions and rules ----------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.OPEN, "open"),
        (S.OPEN, "closed"),
        (S.OPEN, "inconclusive"),
        (S.INVESTIGATING, "investigating"),
        (S.CLOSED, "closed"),
        (S.CLOSED, "investigating"),
        (S.CLOSED, "inconclusive"),
        (S.INCONCLUSIVE, "closed"),
        (S.INCONCLUSIVE, "investigating"),
    ],
)
def test_invalid_transition_returns_422_and_changes_nothing(
    client: TestClient, db: Session, ana: Analyst, current: IncidentStatus, target: str
) -> None:
    incident = make_incident(db, status=current, assigned_to=ana.id)
    note = "Motivo com mais de dez caracteres." if target == "inconclusive" else None

    response = _patch(client, incident, target, ana, note=note)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert f"from {current.value} to {target}" in response.json()["detail"]
    row = _reload(db, incident)
    assert (row.status, row.version) == (current, 1)
    assert _status_events(db, incident) == []


@pytest.mark.parametrize("note", [None, "", "   ", "curta"])
def test_inconclusive_requires_note(
    client: TestClient, db: Session, ana: Analyst, note: str | None
) -> None:
    incident = make_incident(db, status=S.INVESTIGATING, assigned_to=ana.id)

    response = _patch(client, incident, "inconclusive", ana, note=note)

    assert response.status_code == 422
    assert "field 'note'" in response.json()["detail"]
    detail = response.json()["detail"]
    assert "at least 10 characters" in detail
    assert "Value error" not in detail
    assert "Invalid field 'note': A note of at least 10 characters" in detail
    assert _reload(db, incident).status is S.INVESTIGATING


@pytest.mark.parametrize("target", ["open", "closed", "inconclusive"])
def test_only_responsible_can_leave_investigating(
    client: TestClient, db: Session, ana: Analyst, bruno: Analyst, target: str
) -> None:
    incident = make_incident(db, status=S.INVESTIGATING, assigned_to=ana.id)

    response = _patch(client, incident, target, bruno, note="Tentando encerrar o caso.")

    assert response.status_code == 403
    body = response.json()
    assert response.headers["content-type"] == "application/problem+json"
    assert "Ana Souza" in body["detail"]
    assert body["assignee"] == {"id": str(ana.id), "name": "Ana Souza"}
    row = _reload(db, incident)
    assert (row.status, row.version, row.assigned_to) == (S.INVESTIGATING, 1, ana.id)
    assert _status_events(db, incident) == []


def test_unknown_field_is_rejected(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db)

    response = _patch(client, incident, "investigating", ana, assigned_to=str(ana.id))

    assert response.status_code == 422


def test_unknown_analyst_returns_422(client: TestClient, db: Session) -> None:
    incident = make_incident(db)
    ghost = Analyst(id=uuid.uuid4(), name="x", username="x", password_hash="x")

    response = _patch(client, incident, "investigating", ghost)

    assert response.status_code == 422
    assert "Unknown analyst" in response.json()["detail"]


def test_missing_analyst_header_returns_422(client: TestClient, db: Session) -> None:
    incident = make_incident(db)

    assert _patch(client, incident, "investigating", None).status_code == 422


# --- optimistic locking ---------------------------------------------------------------


def test_stale_version_returns_409_with_current_state(
    client: TestClient, db: Session, ana: Analyst, bruno: Analyst
) -> None:
    incident = make_incident(db)
    assert _patch(client, incident, "investigating", ana, version=1).status_code == 200

    response = _patch(client, incident, "investigating", bruno, version=1)

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert "version 1 is outdated (current: 2)" in body["detail"]
    current = body["current"]
    assert current["id"] == str(incident.id)
    assert current["status"] == "investigating"
    assert current["version"] == 2
    assert current["assignee"] == {"id": str(ana.id), "name": "Ana Souza"}
    assert current["updated_at"]
    last = current["events"][-1]
    assert (last["to_status"], last["analyst"]["name"]) == ("investigating", "Ana Souza")
    assert len(_status_events(db, incident)) == 1


def test_stale_version_is_rejected_even_when_transition_looks_valid(
    client: TestClient, db: Session, ana: Analyst, bruno: Analyst
) -> None:
    # Ana takes and releases the incident: it is "open" again, but at version 3.
    incident = make_incident(db)
    assert _patch(client, incident, "investigating", ana, version=1).status_code == 200
    assert _patch(client, incident, "open", ana, version=2).status_code == 200

    # Bruno still has the screen from version 1, where taking it was valid.
    response = _patch(client, incident, "investigating", bruno, version=1)

    assert response.status_code == 409
    assert response.json()["current"]["version"] == 3
    row = _reload(db, incident)
    assert (row.status, row.assigned_to) == (S.OPEN, None)


def test_conflict_takes_precedence_over_responsibility(
    client: TestClient, db: Session, ana: Analyst, bruno: Analyst
) -> None:
    incident = make_incident(db, status=S.INVESTIGATING, assigned_to=ana.id, version=5)

    response = _patch(client, incident, "closed", bruno, version=4)

    assert response.status_code == 409


def test_unknown_incident_returns_404(client: TestClient, ana: Analyst) -> None:
    ghost = Incident(id=uuid.uuid4(), version=1)

    assert _patch(client, ghost, "investigating", ana).status_code == 404


def test_deleted_incident_returns_404(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, deleted_at=EARLIER)

    assert _patch(client, incident, "investigating", ana).status_code == 404
