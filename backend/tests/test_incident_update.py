from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Analyst,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
    Severity,
)
from tests.factories import make_analyst, make_incident

S = IncidentStatus


@pytest.fixture
def ana(db: Session) -> Analyst:
    return make_analyst(db, "ana", "Ana Souza")


def _edit(client: TestClient, incident: Incident, analyst: Analyst, **body: Any):
    body.setdefault("version", incident.version)
    return client.patch(
        f"/incidents/{incident.id}", json=body, headers={"X-Analyst-Id": str(analyst.id)}
    )


def _reload(db: Session, incident: Incident) -> Incident:
    db.expire_all()
    return db.get(Incident, incident.id)


def _updated_events(db: Session, incident: Incident) -> list[IncidentEvent]:
    return list(
        db.scalars(
            select(IncidentEvent).where(
                IncidentEvent.incident_id == incident.id,
                IncidentEvent.event_type == IncidentEventType.UPDATED,
            )
        )
    )


# --- successful edits -----------------------------------------------------------------


def test_edit_changes_fields_bumps_version_and_records_event(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    incident = make_incident(db, severity=Severity.MEDIUM, highway="BR-116", km=Decimal("10.0"))

    response = _edit(client, incident, ana, severity="high", highway="sp 330", km=12.25)

    assert response.status_code == 200
    body = response.json()
    assert (body["severity"], body["highway"], body["km"], body["version"]) == (
        "high",
        "SP-330",
        12.3,
        2,
    )
    [event] = _updated_events(db, incident)
    assert event.analyst_id == ana.id
    assert event.from_status is S.OPEN
    assert event.to_status is None
    assert event.note == 'severity: medium → high; highway: "BR-116" → "SP-330"; km: 10.0 → 12.3'


def test_edit_reports_only_fields_that_changed(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    incident = make_incident(db, severity=Severity.MEDIUM, category=IncidentCategory.ROAD_BLOCKAGE)

    _edit(client, incident, ana, severity="medium", category="adverse_weather")

    [event] = _updated_events(db, incident)
    assert event.note == "category: road_blockage → adverse_weather"


def test_edit_in_investigating_is_allowed(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, status=S.INVESTIGATING, assigned_to=ana.id)

    response = _edit(client, incident, ana, description="Pneu estourado, carga tombou.")

    assert response.status_code == 200
    assert response.json()["description"] == "Pneu estourado, carga tombou."


def test_explicit_null_clears_location(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db)

    response = _edit(client, incident, ana, highway=None, km=None, location_note=None)

    body = response.json()
    assert response.status_code == 200
    assert (body["highway"], body["km"], body["location_note"]) == (None, None, None)


def test_omitted_fields_are_kept(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, highway="BR-116", location_note="Registro/SP")

    _edit(client, incident, ana, severity="high")

    row = _reload(db, incident)
    assert (row.highway, row.location_note) == ("BR-116", "Registro/SP")


# --- location never rejects the edit --------------------------------------------------


def test_invalid_highway_is_nulled_and_appended_to_existing_note(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    incident = make_incident(db, highway="BR-116", location_note="Registro/SP")

    response = _edit(client, incident, ana, highway="BR116 sentido SP")

    body = response.json()
    assert response.status_code == 200
    assert body["highway"] is None
    assert body["location_note"] == "Registro/SP | Rodovia informada: BR116 sentido SP"


def test_invalid_km_is_nulled_and_appended_to_sent_note(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    incident = make_incident(db, location_note="Registro/SP")

    response = _edit(client, incident, ana, km=12000, location_note="Perto do posto")

    body = response.json()
    assert body["km"] is None
    assert body["location_note"] == "Perto do posto | Km informado: 12000"


def test_preserved_value_without_any_note(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, location_note=None)

    body = _edit(client, incident, ana, km="abc").json()

    assert body["location_note"] == "Km informado: abc"


# --- no-op ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"severity": "low"},
        {"highway": "br116", "km": 123.44},  # normalizes to the current values
        {"location_note": "Registro/SP"},
    ],
)
def test_edit_without_real_change_returns_200_without_event(
    client: TestClient, db: Session, ana: Analyst, body: dict[str, Any]
) -> None:
    incident = make_incident(db, severity=Severity.LOW, location_note="Registro/SP")

    response = _edit(client, incident, ana, **body)

    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert _updated_events(db, incident) == []


# --- rejections -----------------------------------------------------------------------


@pytest.mark.parametrize("closed_status", [S.CLOSED, S.INCONCLUSIVE])
def test_closed_incident_cannot_be_edited(
    client: TestClient, db: Session, ana: Analyst, closed_status: IncidentStatus
) -> None:
    incident = make_incident(db, status=closed_status)

    response = _edit(client, incident, ana, severity="high")

    assert response.status_code == 422
    assert "Reopen it first" in response.json()["detail"]
    assert _reload(db, incident).severity is Severity.LOW


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"severity": None}, "severity"),
        ({"severity": "urgent"}, "severity"),
        ({"category": None}, "category"),
        ({"category": "fire"}, "category"),
        ({"description": None}, "description"),
        ({"description": "abc"}, "description"),
        ({"truck_code": "TRK-9"}, "truck_code"),
        ({"status": "closed"}, "status"),
        ({"version": 0}, "version"),
    ],
)
def test_invalid_body_returns_422(
    client: TestClient, db: Session, ana: Analyst, body: dict[str, Any], field: str
) -> None:
    incident = make_incident(db)

    response = _edit(client, incident, ana, **body)

    assert response.status_code == 422
    assert f"field '{field}'" in response.json()["detail"]


def test_missing_version_returns_422(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db)

    response = client.patch(
        f"/incidents/{incident.id}",
        json={"severity": "high"},
        headers={"X-Analyst-Id": str(ana.id)},
    )

    assert response.status_code == 422


def test_stale_version_returns_409_with_current(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    incident = make_incident(db, severity=Severity.LOW)
    assert _edit(client, incident, ana, severity="medium", version=1).status_code == 200

    response = _edit(client, incident, ana, severity="high", version=1)

    assert response.status_code == 409
    current = response.json()["current"]
    assert (current["severity"], current["version"]) == ("medium", 2)
    assert current["events"][-1]["event_type"] == "updated"
    assert _reload(db, incident).severity is Severity.MEDIUM


def test_stale_version_without_changes_is_still_409(
    client: TestClient, db: Session, ana: Analyst
) -> None:
    incident = make_incident(db, version=4)

    assert _edit(client, incident, ana, version=3).status_code == 409


def test_deleted_incident_returns_404(client: TestClient, db: Session, ana: Analyst) -> None:
    incident = make_incident(db, deleted_at=datetime.now(UTC))

    assert _edit(client, incident, ana, severity="high").status_code == 404
