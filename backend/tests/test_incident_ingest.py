import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.main import app
from app.models import Incident, IncidentEvent, IncidentEventType, IncidentStatus
from tests.settings import TEST_INGEST_API_KEY

AUTH = {"X-API-Key": TEST_INGEST_API_KEY}
VALID: dict[str, Any] = {
    "category": "mechanical_failure",
    "severity": "medium",
    "description": "Superaquecimento do motor; caminhão parado no acostamento.",
    "truck_code": "TRK-0420",
    "driver_name": "João Silva",
    "highway": "BR-116",
    "km": 231.5,
    "location_note": "Registro/SP",
}


def _post(client: TestClient, body: dict[str, Any], headers: dict[str, str] = AUTH):
    return client.post("/incidents", json=body, headers=headers)


# --- creation -------------------------------------------------------------------------


def test_create_returns_201_with_location_and_body(client: TestClient, db: Session) -> None:
    response = _post(client, VALID)

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/incidents/{body['id']}"
    assert body["status"] == "open"
    assert body["version"] == 1
    assert body["source"] == "api"
    assert body["highway"] == "BR-116"
    assert body["km"] == 231.5
    assert body["priority_score"] == 50 + 10
    assert client.get(response.headers["location"]).status_code == 200


def test_create_records_created_event_in_same_transaction(client: TestClient, db: Session) -> None:
    incident_id = uuid.UUID(_post(client, VALID).json()["id"])

    events = db.scalars(select(IncidentEvent).where(IncidentEvent.incident_id == incident_id)).all()

    assert len(events) == 1
    assert events[0].event_type is IncidentEventType.CREATED
    assert events[0].from_status is None
    assert events[0].to_status is IncidentStatus.OPEN


def test_create_without_location_or_driver(client: TestClient) -> None:
    body = {k: VALID[k] for k in ("category", "severity", "description", "truck_code")}

    response = _post(client, body | {"source": "whatsapp", "raw_message": "central, pneu furou"})

    assert response.status_code == 201
    created = response.json()
    assert created["highway"] is None
    assert created["km"] is None
    assert created["location_note"] is None
    assert created["driver_name"] is None
    assert created["source"] == "whatsapp"


def test_create_normalizes_input(client: TestClient) -> None:
    response = _post(
        client,
        VALID | {"description": "   Pneu furado no eixo   ", "highway": "sp 330", "km": 12.25},
    )

    created = response.json()
    assert created["description"] == "Pneu furado no eixo"
    assert created["highway"] == "SP-330"
    assert created["km"] == 12.3  # rounded, never rejected


def test_blank_optional_fields_become_null(client: TestClient) -> None:
    created = _post(client, VALID | {"location_note": "  ", "highway": ""}).json()

    assert created["location_note"] is None
    assert created["highway"] is None


# --- location never rejects an incident ----------------------------------------------


@pytest.mark.parametrize(
    ("highway", "expected_note"),
    [
        ("BR116 sentido SP", "Rodovia informada: BR116 sentido SP"),
        ("BR-1160", "Rodovia informada: BR-1160"),
        ("Rodovia dos Bandeirantes", "Rodovia informada: Rodovia dos Bandeirantes"),
    ],
)
def test_invalid_highway_is_stored_as_null_and_preserved(
    client: TestClient, highway: str, expected_note: str
) -> None:
    body = {k: v for k, v in VALID.items() if k != "location_note"}

    response = _post(client, body | {"highway": highway})

    assert response.status_code == 201
    created = response.json()
    assert created["highway"] is None
    assert created["location_note"] == expected_note
    assert created["km"] == 231.5


@pytest.mark.parametrize("km", [-0.1, 10000, "abc", True])
def test_invalid_km_is_stored_as_null_and_preserved(client: TestClient, km: Any) -> None:
    body = {k: v for k, v in VALID.items() if k != "location_note"}

    response = _post(client, body | {"km": km})

    assert response.status_code == 201
    created = response.json()
    assert created["km"] is None
    assert created["location_note"] == f"Km informado: {km}"
    assert created["highway"] == "BR-116"


def test_preserved_location_is_appended_to_existing_note(client: TestClient) -> None:
    response = _post(
        client,
        VALID | {"highway": "BR116 sentido SP", "km": 12000, "location_note": "Perto do posto"},
    )

    created = response.json()
    assert response.status_code == 201
    assert created["highway"] is None
    assert created["km"] is None
    assert created["location_note"] == (
        "Perto do posto | Rodovia informada: BR116 sentido SP | Km informado: 12000"
    )


def test_long_location_note_is_clipped_keeping_preserved_values(client: TestClient) -> None:
    response = _post(client, VALID | {"location_note": "x" * 300, "highway": "Rodovia X"})

    note = response.json()["location_note"]
    assert response.status_code == 201
    assert len(note) == 255
    assert note.endswith("| Rodovia informada: Rodovia X")


def test_km_accepts_decimal_comma(client: TestClient) -> None:
    assert _post(client, VALID | {"km": "15,5"}).json()["km"] == 15.5


# --- validation -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"category": None}, "category"),
        ({"category": "fire"}, "category"),
        ({"severity": None}, "severity"),
        ({"severity": "urgent"}, "severity"),
        ({"description": None}, "description"),
        ({"description": "abc"}, "description"),
        ({"description": "  abcd   "}, "description"),
        ({"description": "x" * 2001}, "description"),
        ({"truck_code": None}, "truck_code"),
        ({"truck_code": "   "}, "truck_code"),
        ({"truck_code": "T" * 21}, "truck_code"),
        ({"source": "email"}, "source"),
    ],
)
def test_invalid_field_returns_422(
    client: TestClient, db: Session, changes: dict[str, Any], field: str
) -> None:
    body = {k: v for k, v in (VALID | changes).items() if v is not None}

    response = _post(client, body)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert f"field '{field}'" in response.json()["detail"]
    assert db.scalar(select(Incident.id)) is None


def test_unknown_field_returns_422(client: TestClient) -> None:
    response = _post(client, VALID | {"priority": "max"})

    assert response.status_code == 422
    assert "field 'priority'" in response.json()["detail"]
    assert "Extra inputs are not permitted" in response.json()["detail"]


def test_status_cannot_be_forced_on_creation(client: TestClient) -> None:
    assert _post(client, VALID | {"status": "closed"}).status_code == 422


# --- authentication -------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-API-Key": "wrong-key"}, {"X-API-Key": ""}],
    ids=["missing", "wrong", "empty"],
)
def test_invalid_api_key_returns_401(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    response = _post(client, VALID, headers=headers)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Missing or invalid API key."
    assert db.scalar(select(Incident.id)) is None


def test_ingestion_is_closed_when_no_key_is_configured(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(ingest_api_key=None)

    assert _post(client, VALID).status_code == 401


def test_auth_is_checked_before_body_validation(client: TestClient) -> None:
    response = _post(client, {"foo": "bar"}, headers={})

    assert response.status_code == 401


def test_openapi_documents_401_for_ingestion() -> None:
    operation = app.openapi()["paths"]["/incidents"]["post"]

    assert "application/problem+json" in operation["responses"]["401"]["content"]
    assert operation["security"] == [{"APIKeyHeader": []}]
