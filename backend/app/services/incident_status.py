"""Status transitions with optimistic locking.

The write is a single atomic statement; the current state is only read afterwards,
when nothing was written, to explain why (404, 409, 403 or 422).
"""

import uuid
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.retry import read_with_retry
from app.models import Incident, IncidentEvent, IncidentEventType, IncidentStatus

S = IncidentStatus

# Valid source states for each target state (see CLAUDE.md).
TRANSITION_SOURCES: dict[IncidentStatus, tuple[IncidentStatus, ...]] = {
    S.INVESTIGATING: (S.OPEN,),
    S.OPEN: (S.INVESTIGATING, S.CLOSED, S.INCONCLUSIVE),
    S.CLOSED: (S.INVESTIGATING,),
    S.INCONCLUSIVE: (S.INVESTIGATING,),
}


class IncidentNotFound(Exception):
    pass


class VersionConflict(Exception):
    def __init__(self, sent_version: int, current: Incident) -> None:
        super().__init__(f"version {sent_version} is outdated (current: {current.version})")
        self.sent_version = sent_version
        self.current = current


class NotResponsible(Exception):
    def __init__(self, current: Incident) -> None:
        super().__init__("only the responsible analyst can change this incident")
        self.current = current


class InvalidTransition(Exception):
    def __init__(self, from_status: IncidentStatus, to_status: IncidentStatus) -> None:
        super().__init__(f"cannot change status from {from_status} to {to_status}")
        self.from_status = from_status
        self.to_status = to_status


def _target_values(target: IncidentStatus, analyst_id: uuid.UUID) -> dict[str, Any]:
    if target is S.INVESTIGATING:
        # Take ownership; acknowledged_at keeps the first reaction (MTTA).
        return {
            "assigned_to": analyst_id,
            "acknowledged_at": func.coalesce(Incident.acknowledged_at, func.now()),
        }
    if target is S.OPEN:
        # Release (from investigating) or reopen (from closed/inconclusive).
        return {"assigned_to": None, "resolved_at": None}
    return {"resolved_at": func.now()}


def change_status(
    db: Session,
    incident_id: uuid.UUID,
    *,
    target: IncidentStatus,
    version: int,
    analyst_id: uuid.UUID,
    note: str | None,
) -> None:
    # Lock the row only if it matches everything the client assumed; inside one
    # statement, so concurrent writers re-check version after the lock is released.
    current = (
        select(Incident.id, Incident.status)
        .where(
            Incident.id == incident_id,
            Incident.version == version,
            Incident.deleted_at.is_(None),
            Incident.status.in_(TRANSITION_SOURCES[target]),
            # Only the responsible analyst can take an incident out of investigating.
            or_(Incident.status != S.INVESTIGATING, Incident.assigned_to == analyst_id),
        )
        .with_for_update()
        .cte("current")
    )
    from_status = db.execute(
        update(Incident)
        .where(Incident.id == current.c.id)
        .values(
            status=target,
            version=Incident.version + 1,
            updated_at=func.now(),
            **_target_values(target, analyst_id),
        )
        # PostgreSQL 16 has no OLD in RETURNING; the CTE row carries the previous status.
        .returning(current.c.status)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()

    if from_status is None:
        # Nothing was written or locked; a fresh read explains why.
        read_with_retry(
            db,
            lambda: _raise_why_not_changed(
                db, incident_id, target=target, version=version, analyst_id=analyst_id
            ),
        )

    db.add(
        IncidentEvent(
            incident_id=incident_id,
            analyst_id=analyst_id,
            event_type=IncidentEventType.STATUS_CHANGED,
            from_status=from_status,
            to_status=target,
            note=note,
        )
    )
    db.commit()


def _raise_why_not_changed(
    db: Session,
    incident_id: uuid.UUID,
    *,
    target: IncidentStatus,
    version: int,
    analyst_id: uuid.UUID,
) -> None:
    incident = db.scalars(
        select(Incident)
        .options(joinedload(Incident.assignee))
        .where(Incident.id == incident_id)
        .execution_options(populate_existing=True)
    ).one_or_none()

    if incident is None or incident.deleted_at is not None:
        raise IncidentNotFound
    if incident.version != version:
        raise VersionConflict(version, incident)
    if (
        incident.status is S.INVESTIGATING
        and incident.status in TRANSITION_SOURCES[target]
        and incident.assigned_to != analyst_id
    ):
        raise NotResponsible(incident)
    raise InvalidTransition(incident.status, target)
