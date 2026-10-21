import uuid
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app
from app.models import (
    Analyst,
    Conversation,
    Incident,
    IncidentCategory,
    IncidentSource,
    IncidentStatus,
    Severity,
    Truck,
)
from app.models.enums import CargoType, ClientTier
from app.services import whatsapp
from app.services.incident_status import change_status
from tests.factories import auth_headers, make_analyst
from tests.settings import TEST_INGEST_API_KEY, TEST_SETTINGS

PHONE = "5511990001001"
AUTH = {"X-API-Key": TEST_INGEST_API_KEY}


def _webhook(client: TestClient, text: str, headers: dict[str, str] = AUTH):
    body = {"from": PHONE, "id": "wamid.1", "type": "text", "text": {"body": text}}
    return client.post("/channels/whatsapp/webhook", json=body, headers=headers)


def _talk(db: Session, *answers: str) -> list[str]:
    replies: list[str] = []
    for answer in answers:
        replies = whatsapp.receive(db, PHONE, answer)
    return replies


FULL = ("oi", "TRK-1001", "1", "sim", "BR-116 km 230", "não", "Batida com moto")


def _incident(db: Session) -> Incident:
    return db.scalars(select(Incident).where(Incident.source == IncidentSource.WHATSAPP)).one()


def test_webhook_requires_the_ingestion_key(anon_client: TestClient) -> None:
    assert _webhook(anon_client, "oi", headers={}).status_code == 401
    assert _webhook(anon_client, "oi", headers={"X-API-Key": "wrong"}).status_code == 401


def test_webhook_answers_with_the_first_question(anon_client: TestClient) -> None:
    response = _webhook(anon_client, "oi")

    assert response.status_code == 200
    assert response.json()["replies"][-1] == "Qual é o código do caminhão? (ex.: TRK-1001)"


def test_webhook_rejects_an_invalid_phone(anon_client: TestClient) -> None:
    body = {"from": "abc", "type": "text", "text": {"body": "oi"}}

    assert (
        anon_client.post("/channels/whatsapp/webhook", json=body, headers=AUTH).status_code == 422
    )


def test_full_conversation_creates_the_incident_with_fleet_data(db: Session) -> None:
    db.add(
        Truck(
            code="TRK-1001",
            cargo_type=CargoType.HAZARDOUS,
            client_name="Química Pinguim Azul",
            client_tier=ClientTier.PRIORITY,
        )
    )
    db.flush()

    replies = _talk(db, *FULL)

    incident = _incident(db)
    assert f"protocolo {whatsapp.protocol(incident.id)}" in replies[0]
    assert incident.category is IncidentCategory.ACCIDENT_WITH_VICTIMS
    assert incident.severity is Severity.HIGH
    assert incident.truck_code == "TRK-1001"
    assert incident.driver_name == "Motorista do TRK-1001 (via WhatsApp)"
    assert PHONE not in incident.driver_name
    assert (incident.highway, float(incident.km)) == ("BR-116", 230.0)
    assert incident.cargo_type is CargoType.HAZARDOUS and incident.fleet_match
    assert incident.raw_message.startswith("Motorista: oi\nBot: Olá!")
    assert "Motorista: Batida com moto" in incident.raw_message


def test_unknown_location_still_creates_the_incident(db: Session) -> None:
    _talk(db, "oi", "TRK-1001", "4", "não", "não sei", "sim", "pular")

    incident = _incident(db)
    assert incident.highway is None and incident.location_note is None
    assert incident.severity is Severity.LOW


def test_a_new_message_after_the_incident_starts_a_new_conversation(db: Session) -> None:
    _talk(db, *FULL)

    replies = _talk(db, "oi de novo")

    assert replies[-1].startswith("Qual é o código do caminhão?")


def test_idle_conversation_starts_over_after_30_minutes(db: Session) -> None:
    _talk(db, "oi", "TRK-1001")
    db.execute(
        update(Conversation).values(updated_at=Conversation.updated_at - timedelta(minutes=31))
    )

    replies = _talk(db, "2")

    assert replies[0].startswith("Olá!")
    assert db.query(Conversation).count() == 2


def test_cancel_creates_nothing(db: Session) -> None:
    _talk(db, "oi", "TRK-1001", "cancelar")

    assert db.query(Incident).count() == 0
    assert whatsapp.thread(db, PHONE).step is None


def test_thread_lists_messages_in_order_with_options(db: Session) -> None:
    _talk(db, "oi", "TRK-1001")

    thread = whatsapp.thread(db, PHONE)

    assert [m.direction.value for m in thread.messages] == ["in", "out", "out", "in", "out"]
    assert thread.step == "problem"
    assert thread.options[0] == "1 Acidente"


def test_driver_hears_when_the_incident_is_taken_and_closed(db: Session) -> None:
    ana = make_analyst(db, "ana.souza", "Ana Souza")
    _talk(db, *FULL)
    incident = _incident(db)
    code = whatsapp.protocol(incident.id)

    change_status(
        db,
        incident.id,
        target=IncidentStatus.INVESTIGATING,
        version=1,
        analyst_id=ana.id,
        note=None,
    )
    change_status(
        db, incident.id, target=IncidentStatus.CLOSED, version=2, analyst_id=ana.id, note=None
    )

    texts = [m.text for m in whatsapp.thread(db, PHONE).messages]
    assert texts[-2] == f"Ana Souza está cuidando do seu chamado {code}."
    assert texts[-1].startswith(f"Seu chamado {code} foi encerrado.")


@pytest.fixture
def demo_api(db: Session, current_analyst: Analyst) -> TestClient:
    app: FastAPI = create_app(TEST_SETTINGS.model_copy(update={"demo_mode": True}))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    client = TestClient(app)
    client.headers.update(auth_headers(current_analyst))
    return client


def test_simulator_sends_and_reads_the_thread(demo_api: TestClient) -> None:
    sent = demo_api.post("/demo/whatsapp/messages", json={"phone": PHONE, "text": "oi"})
    thread = demo_api.get(f"/demo/whatsapp/conversations/{PHONE}/messages")

    assert sent.status_code == 200
    assert thread.status_code == 200
    body = thread.json()
    assert body["step"] == "truck"
    assert [m["direction"] for m in body["messages"]] == ["in", "out", "out"]


def test_simulator_needs_an_analyst_and_demo_mode(demo_api: TestClient, client: TestClient) -> None:
    anonymous = demo_api.post(
        "/demo/whatsapp/messages",
        json={"phone": PHONE, "text": "oi"},
        headers={"Authorization": ""},
    )

    assert anonymous.status_code == 401
    assert (
        client.post("/demo/whatsapp/messages", json={"phone": PHONE, "text": "oi"}).status_code
        == 404
    )


def test_simulator_lists_the_fleet(demo_api: TestClient, db: Session) -> None:
    db.add(
        Truck(
            code="TRK-1001",
            cargo_type=CargoType.PERISHABLE,
            client_name="Frigorífico Boi Celeste",
            client_tier=ClientTier.PRIORITY,
        )
    )
    db.flush()

    assert demo_api.get("/demo/fleet").json() == [
        {
            "code": "TRK-1001",
            "cargo_type": "perishable",
            "client_name": "Frigorífico Boi Celeste",
            "client_tier": "priority",
        }
    ]


def test_simulator_lists_recent_conversations_with_their_truck(
    demo_api: TestClient, db: Session
) -> None:
    whatsapp.receive(db, "5511990001002", "oi")  # no truck yet
    _talk(db, "oi", "TRK-1001")

    recent = demo_api.get("/demo/whatsapp/conversations").json()

    assert [c["phone"] for c in recent] == [PHONE, "5511990001002"]
    assert recent[0]["truck_code"] == "TRK-1001"
    assert recent[1]["truck_code"] is None
    assert recent[0]["last_out_at"] is not None


def test_simulator_finds_the_conversation_of_an_incident(demo_api: TestClient, db: Session) -> None:
    _talk(db, *FULL)
    incident = _incident(db)

    found = demo_api.get(f"/demo/whatsapp/incidents/{incident.id}/conversation")
    missing = demo_api.get(f"/demo/whatsapp/incidents/{uuid.uuid4()}/conversation")

    assert found.json() == {"phone": PHONE}
    assert missing.status_code == 404
    assert missing.headers["content-type"] == "application/problem+json"
