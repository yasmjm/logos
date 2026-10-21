import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Analyst,
    CargoType,
    ClientTier,
    Incident,
    IncidentEvent,
    IncidentEventType,
    IncidentSource,
    Truck,
)

VALID: dict[str, Any] = {
    "category": "mechanical_failure",
    "severity": "medium",
    "description": "Motorista ligou: superaquecimento do motor no acostamento.",
    "truck_code": "TRK-1001",
    "highway": "BR-116",
    "km": 231.5,
    "location_note": "Registro/SP",
}


def _post(client: TestClient, body: dict[str, Any], **kwargs: Any):
    return client.post("/incidents/manual", json=body, **kwargs)


def test_analyst_creates_a_manual_incident_with_fleet_data(client: TestClient, db: Session) -> None:
    db.add(
        Truck(
            code="TRK-1001",
            cargo_type=CargoType.PERISHABLE,
            client_name="Frigorífico Boi Celeste",
            client_tier=ClientTier.PRIORITY,
        )
    )
    db.flush()

    response = _post(client, {**VALID, "source": "api", "raw_message": "ignored"})

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/incidents/{body['id']}"
    assert body["source"] == "manual"
    assert body["raw_message"] is None
    assert body["cargo_type"] == "perishable" and body["fleet_match"] is True
    assert body["highway"] == "BR-116"


def test_created_event_names_the_analyst(
    client: TestClient, db: Session, current_analyst: Analyst
) -> None:
    incident_id = uuid.UUID(_post(client, VALID).json()["id"])

    event = db.scalars(
        select(IncidentEvent).where(
            IncidentEvent.incident_id == incident_id,
            IncidentEvent.event_type == IncidentEventType.CREATED,
        )
    ).one()
    assert event.analyst_id == current_analyst.id
    assert db.get(Incident, incident_id).source is IncidentSource.MANUAL


def test_manual_creation_requires_an_analyst(anon_client: TestClient) -> None:
    assert _post(anon_client, VALID).status_code == 401


def test_essential_fields_are_validated(client: TestClient) -> None:
    response = _post(client, {**VALID, "category": "alien", "description": "x", "truck_code": ""})

    assert response.status_code == 422
    locations = {error["location"] for error in response.json()["errors"]}
    assert {"field 'category'", "field 'description'", "field 'truck_code'"} <= locations


def test_unusable_location_never_rejects_the_incident(client: TestClient) -> None:
    response = _post(client, {**VALID, "highway": "estrada velha", "km": "perto do posto"})

    assert response.status_code == 201
    body = response.json()
    assert body["highway"] is None and body["km"] is None
    assert "Rodovia informada: estrada velha" in body["location_note"]


def test_analysts_list_the_fleet(client: TestClient, db: Session) -> None:
    db.add(
        Truck(
            code="TRK-1001",
            cargo_type=CargoType.EMPTY,
            client_name="Grãos Siriema Dourada",
            client_tier=ClientTier.STANDARD,
        )
    )
    db.flush()

    assert [t["code"] for t in client.get("/fleet").json()] == ["TRK-1001"]
