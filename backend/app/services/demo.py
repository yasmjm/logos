"""Evaluator tools (DEMO_MODE): refresh the demo data and simulate new reports.

Nothing here deletes history: a reset soft-deletes the visible incidents (with a
"deleted" event naming the analyst who asked) and creates a fresh demo set.
"""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Incident, IncidentEvent, IncidentEventType, Truck
from app.schemas.incident_create import IncidentCreate
from app.seed import add_demo_incidents, ensure_analysts, random_incident_fields
from app.services.incidents import create_incident

RESET_NOTE = "Demo reset"


@dataclass(frozen=True)
class ResetResult:
    deleted: int
    created: int


def reset_demo_data(db: Session, analyst_id: uuid.UUID) -> ResetResult:
    """Soft-delete every visible incident and create the demo set relative to now,
    all in one transaction."""
    previous = db.execute(
        update(Incident)
        .where(Incident.deleted_at.is_(None))
        .values(deleted_at=func.now(), version=Incident.version + 1)
        .returning(Incident.id, Incident.status)
        .execution_options(synchronize_session=False)
    ).all()
    db.add_all(
        IncidentEvent(
            incident_id=incident_id,
            analyst_id=analyst_id,
            event_type=IncidentEventType.DELETED,
            from_status=status,
            to_status=None,
            note=RESET_NOTE,
        )
        for incident_id, status in previous
    )
    created = add_demo_incidents(db, ensure_analysts(db), datetime.now(UTC))
    db.commit()
    return ResetResult(deleted=len(previous), created=created)


def simulate_incidents(db: Session, count: int, rng: random.Random) -> list[uuid.UUID]:
    """New reports from the seed templates, through the same path as public ingestion."""
    truck_codes = list(db.scalars(select(Truck.code)))
    return [
        create_incident(db, IncidentCreate(**random_incident_fields(rng, truck_codes=truck_codes)))
        for _ in range(count)
    ]
