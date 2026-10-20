import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Integer, Select, case, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
    Severity,
)
from app.schemas.incident_create import IncidentCreate

SEVERITY_WEIGHTS = {Severity.HIGH: 100, Severity.MEDIUM: 50, Severity.LOW: 10}
CATEGORY_WEIGHTS = {
    IncidentCategory.ACCIDENT_WITH_VICTIMS: 40,
    IncidentCategory.VEHICLE_ACCIDENT: 25,
    IncidentCategory.ROAD_BLOCKAGE: 20,
    IncidentCategory.ADVERSE_WEATHER: 15,
    IncidentCategory.MECHANICAL_FAILURE: 10,
}
MAX_AGING_POINTS = 60
ACTIVE_STATUSES = (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)
RESOLVED_STATUSES = (IncidentStatus.CLOSED, IncidentStatus.INCONCLUSIVE)


def priority_score_expr() -> ColumnElement[int]:
    """Priority score computed in the database.

    severity weight + category weight + aging, where aging is 1 point per minute
    waiting for a reaction (created_at until acknowledged_at, or now() if nobody
    took it yet), capped at 60. Resolved incidents get no aging.
    """
    severity_weight = case(SEVERITY_WEIGHTS, value=Incident.severity, else_=0)
    category_weight = case(CATEGORY_WEIGHTS, value=Incident.category, else_=0)
    waiting_minutes = func.floor(
        func.extract(
            "epoch", func.coalesce(Incident.acknowledged_at, func.now()) - Incident.created_at
        )
        / 60
    )
    aging = case(
        (Incident.status.in_(RESOLVED_STATUSES), 0),
        else_=func.least(MAX_AGING_POINTS, func.greatest(0, waiting_minutes)),
    )
    return cast(severity_weight + category_weight + aging, Integer)


def _not_deleted() -> ColumnElement[bool]:
    return Incident.deleted_at.is_(None)


@dataclass(frozen=True)
class IncidentFilters:
    severities: list[Severity] | None = None
    categories: list[IncidentCategory] | None = None
    statuses: list[IncidentStatus] | None = None
    assigned_to: uuid.UUID | None = None

    def apply(self, stmt: Select) -> Select:
        stmt = stmt.where(_not_deleted())
        if self.severities:
            stmt = stmt.where(Incident.severity.in_(self.severities))
        if self.categories:
            stmt = stmt.where(Incident.category.in_(self.categories))
        if self.statuses:
            stmt = stmt.where(Incident.status.in_(self.statuses))
        if self.assigned_to is not None:
            stmt = stmt.where(Incident.assigned_to == self.assigned_to)
        return stmt


def list_incidents(
    db: Session, filters: IncidentFilters, limit: int, offset: int
) -> tuple[list[tuple[Incident, int]], int]:
    score = priority_score_expr().label("priority_score")
    is_resolved = case((Incident.status.in_(RESOLVED_STATUSES), 1), else_=0)

    stmt = (
        filters.apply(select(Incident, score))
        .options(joinedload(Incident.assignee))
        .order_by(is_resolved, score.desc(), Incident.created_at, Incident.id)
        .limit(limit)
        .offset(offset)
    )
    rows = [(incident, priority) for incident, priority in db.execute(stmt).all()]
    total = db.scalar(filters.apply(select(func.count()).select_from(Incident)))
    return rows, total or 0


def get_incident(
    db: Session, incident_id: uuid.UUID
) -> tuple[Incident, int, list[IncidentEvent]] | None:
    row = db.execute(
        select(Incident, priority_score_expr())
        .options(joinedload(Incident.assignee))
        .where(Incident.id == incident_id, _not_deleted())
    ).one_or_none()
    if row is None:
        return None

    incident, priority = row
    events = list(
        db.scalars(
            select(IncidentEvent)
            .options(joinedload(IncidentEvent.analyst))
            .where(IncidentEvent.incident_id == incident_id)
            .order_by(IncidentEvent.created_at, IncidentEvent.id)
        )
    )
    return incident, priority, events


def get_active_summary(db: Session) -> tuple[int, dict[Severity, int], dict[IncidentCategory, int]]:
    active = (Incident.status.in_(ACTIVE_STATUSES), _not_deleted())

    by_severity = dict.fromkeys(Severity, 0)
    for severity, count in db.execute(
        select(Incident.severity, func.count()).where(*active).group_by(Incident.severity)
    ):
        by_severity[severity] = count

    by_category = dict.fromkeys(IncidentCategory, 0)
    for category, count in db.execute(
        select(Incident.category, func.count()).where(*active).group_by(Incident.category)
    ):
        by_category[category] = count

    return sum(by_severity.values()), by_severity, by_category


def create_incident(db: Session, data: IncidentCreate) -> uuid.UUID:
    """Insert the incident and its "created" event in a single transaction."""
    incident = Incident(
        id=uuid.uuid4(),
        **data.model_dump(),
        status=IncidentStatus.OPEN,
        version=1,
    )
    db.add(incident)
    db.flush()
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            event_type=IncidentEventType.CREATED,
            from_status=None,
            to_status=IncidentStatus.OPEN,
        )
    )
    db.commit()
    return incident.id
