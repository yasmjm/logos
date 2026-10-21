import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.tokens import create_access_token
from app.models import (
    Analyst,
    CargoType,
    ClientTier,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
    Severity,
    Truck,
)
from tests.settings import TEST_SETTINGS

_DEFAULT_PASSWORD_HASH = hash_password("x")


def auth_headers(analyst: Analyst) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(analyst.id, TEST_SETTINGS)}"}


def make_analyst(
    db: Session, username: str = "ana", name: str = "Ana Souza", password: str | None = None
) -> Analyst:
    # Hashing is slow on purpose (scrypt); reuse one hash unless a real password is needed.
    password_hash = hash_password(password) if password else _DEFAULT_PASSWORD_HASH
    analyst = Analyst(id=uuid.uuid4(), name=name, username=username, password_hash=password_hash)
    db.add(analyst)
    db.flush()
    return analyst


def make_incident(
    db: Session,
    *,
    severity: Severity = Severity.LOW,
    category: IncidentCategory = IncidentCategory.MECHANICAL_FAILURE,
    status: IncidentStatus = IncidentStatus.OPEN,
    age: timedelta = timedelta(0),
    **overrides: Any,
) -> Incident:
    # created_at is taken before Postgres now() would be reached by the query; the extra
    # 30 seconds keeps floor(minutes) stable regardless of that small clock difference.
    created_at = datetime.now(UTC) - age - timedelta(seconds=30)
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "description": "Pneu estourado no eixo traseiro.",
        "category": category,
        "severity": severity,
        "status": status,
        "truck_code": "TRK-0001",
        "driver_name": "João Silva",
        "highway": "BR-116",
        "km": Decimal("123.4"),
        "location_note": "Registro/SP",
        "created_at": created_at,
        "updated_at": created_at,
    }
    fields.update(overrides)
    incident = Incident(**fields)
    db.add(incident)
    db.flush()
    return incident


def make_event(
    db: Session,
    incident: Incident,
    *,
    to_status: IncidentStatus,
    from_status: IncidentStatus | None = None,
    at: datetime,
    analyst: Analyst | None = None,
    note: str | None = None,
) -> IncidentEvent:
    event = IncidentEvent(
        incident_id=incident.id,
        analyst_id=analyst.id if analyst else None,
        event_type=IncidentEventType.CREATED
        if from_status is None
        else IncidentEventType.STATUS_CHANGED,
        from_status=from_status,
        to_status=to_status,
        note=note,
        created_at=at,
    )
    db.add(event)
    db.flush()
    return event


def make_truck(
    db: Session,
    code: str = "TRK-0420",
    cargo_type: CargoType = CargoType.GENERAL,
    client_name: str = "Papelaria Capivara Sonhadora",
    client_tier: ClientTier = ClientTier.STANDARD,
) -> Truck:
    truck = Truck(
        code=code, cargo_type=cargo_type, client_name=client_name, client_tier=client_tier
    )
    db.add(truck)
    db.flush()
    return truck
