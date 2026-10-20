"""Editing incident fields with optimistic locking.

Same pattern as status changes: one atomic UPDATE that only touches a row matching
the client's version and holding a real change; the state is read afterwards only
to explain why nothing was written.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, case, func, literal, or_, select, update
from sqlalchemy.orm import Session

from app.core.retry import read_with_retry
from app.models import Incident, IncidentEvent, IncidentEventType, IncidentStatus
from app.schemas.incident_create import NOTE_SEPARATOR, clip, room_for_note
from app.schemas.incident_update import IncidentUpdate
from app.services.incident_status import IncidentNotFound, VersionConflict

EDITABLE_STATUSES = (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)


class IncidentNotEditable(Exception):
    def __init__(self, status: IncidentStatus) -> None:
        super().__init__(f"{status} incidents cannot be edited")
        self.status = status


def _location_note_value(payload: IncidentUpdate) -> ColumnElement[str | None] | str | None:
    """New location_note: the sent value (or the current one) plus preserved values."""
    notes = payload.location_notes
    sent = "location_note" in payload.model_fields_set
    if not notes:
        return payload.location_note
    suffix = NOTE_SEPARATOR.join(notes)
    base = literal(payload.location_note) if sent else Incident.location_note
    return case(
        (base.is_(None), suffix),
        else_=func.left(base, room_for_note(notes)) + NOTE_SEPARATOR + suffix,
    )


def _describe(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, str):
        return f'"{clip(value, 40)}"'
    return str(value)


def update_incident(
    db: Session, incident_id: uuid.UUID, payload: IncidentUpdate, analyst_id: uuid.UUID
) -> bool:
    """Apply the edit. Returns False when the body holds no real change."""
    values: dict[str, Any] = payload.changes()
    if payload.location_notes or "location_note" in values:
        values["location_note"] = _location_note_value(payload)

    if values:
        current = (
            select(Incident.id, Incident.status, *(getattr(Incident, f) for f in values))
            .where(
                Incident.id == incident_id,
                Incident.version == payload.version,
                Incident.deleted_at.is_(None),
                Incident.status.in_(EDITABLE_STATUSES),
            )
            .with_for_update()
            .cte("current")
        )
        row = db.execute(
            update(Incident)
            .where(
                Incident.id == current.c.id,
                # Only write (and bump version) when something really changes.
                or_(*(getattr(Incident, f).is_distinct_from(v) for f, v in values.items())),
            )
            .values(**values, version=Incident.version + 1, updated_at=func.now())
            .returning(
                current.c.status,
                *(getattr(current.c, f) for f in values),
                *(getattr(Incident, f) for f in values),
            )
            .execution_options(synchronize_session=False)
        ).one_or_none()

        if row is not None:
            status, *pairs = row
            old, new = pairs[: len(values)], pairs[len(values) :]
            changed = [
                f"{field}: {_describe(before)} → {_describe(after)}"
                for field, before, after in zip(values, old, new, strict=True)
                if before != after
            ]
            db.add(
                IncidentEvent(
                    incident_id=incident_id,
                    analyst_id=analyst_id,
                    event_type=IncidentEventType.UPDATED,
                    from_status=status,
                    to_status=None,
                    note="; ".join(changed),
                )
            )
            db.commit()
            return True

    read_with_retry(db, lambda: _raise_unless_unchanged(db, incident_id, payload.version))
    return False


def _raise_unless_unchanged(db: Session, incident_id: uuid.UUID, version: int) -> None:
    incident = db.scalars(
        select(Incident).where(Incident.id == incident_id).execution_options(populate_existing=True)
    ).one_or_none()
    if incident is None or incident.deleted_at is not None:
        raise IncidentNotFound
    if incident.version != version:
        raise VersionConflict(version, incident)
    if incident.status not in EDITABLE_STATUSES:
        raise IncidentNotEditable(incident.status)
    # Otherwise the row matched but nothing differed: a no-op edit.
