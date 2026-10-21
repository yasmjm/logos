from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CargoType, ClientTier, Incident
from tests.factories import make_truck
from tests.settings import TEST_INGEST_API_KEY

BODY = {
    "category": "mechanical_failure",
    "severity": "low",
    "description": "Pneu furado no eixo traseiro.",
}


def _ingest(client: TestClient, truck_code: str):
    return client.post(
        "/incidents",
        json=BODY | {"truck_code": truck_code},
        headers={"X-API-Key": TEST_INGEST_API_KEY},
    )


def test_incident_copies_cargo_and_client_from_the_fleet(client: TestClient, db: Session) -> None:
    make_truck(
        db, "TRK-0101", CargoType.PERISHABLE, "Laticínios Vaca Estrela", ClientTier.STRATEGIC
    )

    body = _ingest(client, "TRK-0101").json()

    assert body["cargo_type"] == "perishable"
    assert body["client_name"] == "Laticínios Vaca Estrela"
    assert body["client_tier"] == "strategic"
    assert body["fleet_match"] is True


def test_unknown_truck_gets_neutral_defaults_and_a_marker(client: TestClient) -> None:
    body = _ingest(client, "TRK-9999").json()

    assert body["cargo_type"] == "general"
    assert body["client_tier"] == "standard"
    assert body["client_name"] is None
    assert body["fleet_match"] is False


def test_snapshot_does_not_follow_later_fleet_changes(client: TestClient, db: Session) -> None:
    truck = make_truck(
        db, "TRK-0102", CargoType.HAZARDOUS, "Química Pinguim Azul", ClientTier.PRIORITY
    )
    incident_id = _ingest(client, "TRK-0102").json()["id"]

    # Next trip: same truck, different cargo and client.
    truck.cargo_type = CargoType.EMPTY
    truck.client_tier = ClientTier.STANDARD
    db.flush()

    db.expire_all()
    incident = db.get(Incident, incident_id)
    assert (incident.cargo_type, incident.client_tier) == (CargoType.HAZARDOUS, ClientTier.PRIORITY)
    assert client.get(f"/incidents/{incident_id}").json()["cargo_type"] == "hazardous"
