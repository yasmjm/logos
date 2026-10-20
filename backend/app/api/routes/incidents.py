import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AnalystIdHeader, DbSession
from app.models import IncidentCategory, IncidentStatus, Severity
from app.schemas.incident import (
    IncidentDetail,
    IncidentListResponse,
    IncidentOut,
    IncidentSummary,
)
from app.services import incidents as incident_service
from app.services.incidents import IncidentFilters

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    db: DbSession,
    analyst_id: AnalystIdHeader = None,
    severity: Annotated[list[Severity] | None, Query()] = None,
    category: Annotated[list[IncidentCategory] | None, Query()] = None,
    status_: Annotated[list[IncidentStatus] | None, Query(alias="status")] = None,
    assigned_to: Literal["me"] | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncidentListResponse:
    if assigned_to == "me" and analyst_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The X-Analyst-Id header is required when assigned_to=me.",
        )

    filters = IncidentFilters(
        severities=severity,
        categories=category,
        statuses=status_,
        assigned_to=analyst_id if assigned_to == "me" else None,
    )
    rows, total = incident_service.list_incidents(db, filters, limit, offset)
    return IncidentListResponse(
        items=[IncidentOut.from_row(incident, score) for incident, score in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# Declared before /{incident_id} so "summary" is not parsed as an id.
@router.get("/summary", response_model=IncidentSummary)
def incidents_summary(db: DbSession) -> IncidentSummary:
    total, by_severity, by_category = incident_service.get_active_summary(db)
    return IncidentSummary(total_active=total, by_severity=by_severity, by_category=by_category)


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: uuid.UUID, db: DbSession) -> IncidentDetail:
    found = incident_service.get_incident(db, incident_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Incident {incident_id} not found.")
    incident, score, events = found
    return IncidentDetail.from_parts(incident, score, events)
