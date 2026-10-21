from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session

from app.domain.sla import ESCALATION_MINUTES, SLA_MINUTES
from app.models import Incident, IncidentStatus, Severity

WINDOW = timedelta(hours=24)
RESOLVED = (IncidentStatus.CLOSED, IncidentStatus.INCONCLUSIVE)


@dataclass(frozen=True)
class Metrics:
    mtta_seconds: float | None
    mtta_count: int
    mttr_seconds: float | None
    mttr_count: int
    escalated_now: int
    sla_breached_now: int


def _seconds(later, earlier):
    return func.extract("epoch", later - earlier)


def compute_metrics(db: Session) -> Metrics:
    """All metrics in one query, computed by Postgres, ignoring soft-deleted incidents."""
    now = func.now()
    since = now - WINDOW
    acknowledged = Incident.acknowledged_at >= since
    # resolved_at is cleared on reopen, so this only sees incidents resolved right now.
    resolved = Incident.status.in_(RESOLVED) & (Incident.resolved_at >= since)
    unowned_open = (Incident.status == IncidentStatus.OPEN) & Incident.assigned_to.is_(None)
    sla_deadline = now - case(
        {severity: timedelta(minutes=minutes) for severity, minutes in SLA_MINUTES.items()},
        value=Incident.severity,
    )

    row = db.execute(
        select(
            func.avg(_seconds(Incident.acknowledged_at, Incident.created_at)).filter(acknowledged),
            func.count().filter(acknowledged),
            func.avg(_seconds(Incident.resolved_at, Incident.created_at)).filter(resolved),
            func.count().filter(resolved),
            cast(
                func.count().filter(
                    unowned_open
                    & (Incident.severity == Severity.HIGH)
                    & (Incident.created_at < now - timedelta(minutes=ESCALATION_MINUTES))
                ),
                Integer,
            ),
            cast(func.count().filter(unowned_open & (Incident.created_at < sla_deadline)), Integer),
        ).where(Incident.deleted_at.is_(None))
    ).one()

    mtta, mtta_count, mttr, mttr_count, escalated, breached = row
    return Metrics(
        mtta_seconds=float(mtta) if mtta is not None else None,
        mtta_count=mtta_count,
        mttr_seconds=float(mttr) if mttr is not None else None,
        mttr_count=mttr_count,
        escalated_now=escalated,
        sla_breached_now=breached,
    )
