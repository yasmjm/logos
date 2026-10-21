import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Integer, Numeric, Select, case, cast, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.domain.priority import (
    CARGO_POINTS,
    CLIENT_POINTS,
    PROBLEM_POINTS,
    VICTIMS_PROBLEM_POINTS,
    VICTIMS_SCORE,
    WAIT_BONUS_CAP,
    WAIT_BONUS_PER_MINUTE,
    WEIGHT_TOTAL,
    WEIGHTS,
)
from app.models import (
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
    Severity,
)
from app.schemas.incident_create import IncidentCreate
from app.services.fleet import snapshot_fleet

ACTIVE_STATUSES = (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)
RESOLVED_STATUSES = (IncidentStatus.CLOSED, IncidentStatus.INCONCLUSIVE)


@dataclass(frozen=True)
class Priority:
    """Score and its breakdown, as computed by the database."""

    score: int
    cargo_points: int
    problem_points: int
    client_points: int
    base: float
    wait_bonus: int
    victims: bool


def _priority_columns() -> list[ColumnElement]:
    """Business-impact priority (app/domain/priority.py), computed in Postgres."""
    cargo = case(CARGO_POINTS, value=Incident.cargo_type, else_=0)
    client = case(CLIENT_POINTS, value=Incident.client_tier, else_=0)
    problem = case(
        *[
            ((Incident.category == category) & (Incident.severity == severity), points)
            for category, by_severity in PROBLEM_POINTS.items()
            for severity, points in by_severity.items()
        ],
        else_=VICTIMS_PROBLEM_POINTS,
    )
    # numeric (not double) so Postgres can round it to one decimal place.
    base = cast(
        (WEIGHTS["cargo"] * cargo + WEIGHTS["problem"] * problem + WEIGHTS["client"] * client)
        / WEIGHT_TOTAL,
        Numeric,
    )
    # Minutes waiting for a reaction: until acknowledged_at, or now if nobody took it.
    waiting_minutes = func.floor(
        func.extract(
            "epoch", func.coalesce(Incident.acknowledged_at, func.now()) - Incident.created_at
        )
        / 60
    )
    wait_bonus = case(
        (Incident.status.in_(RESOLVED_STATUSES), 0),
        else_=func.least(WAIT_BONUS_CAP, func.greatest(0, waiting_minutes * WAIT_BONUS_PER_MINUTE)),
    )
    victims = (Incident.category == IncidentCategory.ACCIDENT_WITH_VICTIMS) & Incident.status.in_(
        ACTIVE_STATUSES
    )
    score = case((victims, VICTIMS_SCORE), else_=func.round(base + wait_bonus))
    return [
        cast(score, Integer).label("priority_score"),
        cast(cargo, Integer).label("cargo_points"),
        cast(problem, Integer).label("problem_points"),
        cast(client, Integer).label("client_points"),
        func.round(base, 1).label("base"),
        cast(wait_bonus, Integer).label("wait_bonus"),
        victims.label("victims"),
    ]


def _priority(row) -> Priority:
    score, cargo, problem, client, base, wait, victims = row
    return Priority(score, cargo, problem, client, float(base), wait, bool(victims))


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
) -> tuple[list[tuple[Incident, Priority]], int]:
    columns = _priority_columns()
    score, victims = columns[0], columns[-1]
    is_resolved = case((Incident.status.in_(RESOLVED_STATUSES), 1), else_=0)
    # Among active victims (all at the same fixed score): nobody on it yet comes first.
    owned_victims = case((victims & Incident.assigned_to.is_not(None), 1), else_=0)

    stmt = (
        filters.apply(select(Incident, *columns))
        .options(joinedload(Incident.assignee))
        # Resolved last; then priority (victims at 200, unowned victims first);
        # ties: the oldest first.
        .order_by(is_resolved, score.desc(), owned_victims, Incident.created_at, Incident.id)
        .limit(limit)
        .offset(offset)
    )
    rows = [(row[0], _priority(row[1:])) for row in db.execute(stmt).all()]
    total = db.scalar(filters.apply(select(func.count()).select_from(Incident)))
    return rows, total or 0


def get_incident(
    db: Session, incident_id: uuid.UUID
) -> tuple[Incident, Priority, list[IncidentEvent]] | None:
    row = db.execute(
        select(Incident, *_priority_columns())
        .options(joinedload(Incident.assignee))
        .where(Incident.id == incident_id, _not_deleted())
    ).one_or_none()
    if row is None:
        return None

    incident, priority = row[0], _priority(row[1:])
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
        # A copy, not a reference: the cargo changes every trip.
        **snapshot_fleet(db, data.truck_code).as_fields(),
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


def soft_delete_incident(db: Session, incident_id: uuid.UUID, analyst_id: uuid.UUID) -> bool:
    """Mark the incident as deleted and record a "deleted" event.

    A single conditional UPDATE (no check-then-act): if the incident does not exist or
    was already deleted, no row is affected and nothing is written. The version bump
    makes any in-flight status change with the old version fail with 409.
    """
    previous_status = db.execute(
        update(Incident)
        .where(Incident.id == incident_id, _not_deleted())
        .values(deleted_at=func.now(), version=Incident.version + 1)
        .returning(Incident.status)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if previous_status is None:
        db.rollback()
        return False

    db.add(
        IncidentEvent(
            incident_id=incident_id,
            analyst_id=analyst_id,
            event_type=IncidentEventType.DELETED,
            from_status=previous_status,
            to_status=None,
        )
    )
    db.commit()
    return True
