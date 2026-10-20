import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Analyst,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
    Severity,
)


def make_analyst(db: Session, username: str = "ana", name: str = "Ana Souza") -> Analyst:
    analyst = Analyst(
        id=uuid.uuid4(), name=name, username=username, password_hash=hash_password("x")
    )
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
