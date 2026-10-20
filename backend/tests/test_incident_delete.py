import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analyst, Incident, IncidentEvent, IncidentEventType, IncidentStatus
from tests.factories import auth_headers, make_analyst, make_incident


def _delete(client: TestClient, incident_id: uuid.UUID, analyst: Analyst):
    return client.delete(f"/incidents/{incident_id}", headers=auth_headers(analyst))


def test_soft_delete_keeps_row_and_records_event(client: TestClient, db: Session) -> None:
    ana = make_analyst(db)
    incident = make_incident(db, status=IncidentStatus.INVESTIGATING, version=2)

    response = _delete(client, incident.id, ana)

    assert response.status_code == 204
    assert response.content == b""
    db.expire_all()
    row = db.get(Incident, incident.id)
    assert row is not None
    assert row.deleted_at is not None
    assert row.status is IncidentStatus.INVESTIGATING
    assert row.version == 3

    event = db.scalars(
        select(IncidentEvent).where(IncidentEvent.event_type == IncidentEventType.DELETED)
    ).one()
    assert event.incident_id == incident.id
    assert event.analyst_id == ana.id
    assert event.from_status is IncidentStatus.INVESTIGATING
    assert event.to_status is None


def test_deleted_incident_disappears_from_listing_and_detail(
    client: TestClient, db: Session
) -> None:
    ana = make_analyst(db)
    kept = make_incident(db)
    removed = make_incident(db)

    _delete(client, removed.id, ana)

    listing = client.get("/incidents").json()
    assert [item["id"] for item in listing["items"]] == [str(kept.id)]
    assert listing["total"] == 1
    assert client.get(f"/incidents/{removed.id}").status_code == 404


def test_deleting_twice_returns_404_and_records_one_event(client: TestClient, db: Session) -> None:
    ana = make_analyst(db)
    incident = make_incident(db)

    assert _delete(client, incident.id, ana).status_code == 204
    second = _delete(client, incident.id, ana)

    assert second.status_code == 404
    assert second.headers["content-type"] == "application/problem+json"
    deleted_events = db.scalars(
        select(IncidentEvent).where(IncidentEvent.event_type == IncidentEventType.DELETED)
    ).all()
    assert len(deleted_events) == 1


def test_deleting_unknown_incident_returns_404(client: TestClient, db: Session) -> None:
    ana = make_analyst(db)

    assert _delete(client, uuid.uuid4(), ana).status_code == 404


def test_delete_requires_authentication(anon_client: TestClient, db: Session) -> None:
    incident = make_incident(db)

    response = anon_client.delete(f"/incidents/{incident.id}")

    assert response.status_code == 401
    db.expire_all()
    assert db.get(Incident, incident.id).deleted_at is None
