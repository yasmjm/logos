import uuid
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import CurrentAnalyst, DbSession, limit_ingestion
from app.api.responses import problem_responses
from app.core.errors import ProblemException
from app.core.retry import read_with_retry
from app.models import IncidentCategory, IncidentStatus, Severity
from app.schemas.incident import (
    AnalystRef,
    IncidentDetail,
    IncidentListResponse,
    IncidentOut,
    IncidentSummary,
)
from app.schemas.incident_create import IncidentCreate
from app.schemas.incident_status import StatusChange
from app.schemas.incident_update import IncidentUpdate
from app.schemas.metrics import IncidentMetrics
from app.services import incident_status, incident_update
from app.services import incidents as incident_service
from app.services.incidents import IncidentFilters
from app.services.metrics import compute_metrics

# Every route here is authenticated (analyst token, or X-API-Key for ingestion).
router = APIRouter(prefix="/incidents", tags=["incidents"], responses=problem_responses(401, 503))


@router.get("", response_model=IncidentListResponse, responses=problem_responses(422))
def list_incidents(
    db: DbSession,
    analyst: CurrentAnalyst,
    severity: Annotated[list[Severity] | None, Query()] = None,
    category: Annotated[list[IncidentCategory] | None, Query()] = None,
    status_: Annotated[list[IncidentStatus] | None, Query(alias="status")] = None,
    assigned_to: Literal["me"] | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncidentListResponse:
    filters = IncidentFilters(
        severities=severity,
        categories=category,
        statuses=status_,
        assigned_to=analyst.id if assigned_to == "me" else None,
    )
    rows, total = read_with_retry(
        db, lambda: incident_service.list_incidents(db, filters, limit, offset)
    )
    return IncidentListResponse(
        items=[IncidentOut.from_row(incident, score) for incident, score in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# Declared before /{incident_id} so "summary" is not parsed as an id.
@router.get(
    "/metrics",
    response_model=IncidentMetrics,
    summary="MTTA and MTTR (last 24 h) and incidents needing attention now",
)
def incidents_metrics(db: DbSession, _: CurrentAnalyst) -> IncidentMetrics:
    metrics = read_with_retry(db, lambda: compute_metrics(db))
    return IncidentMetrics(**asdict(metrics))


@router.get("/summary", response_model=IncidentSummary)
def incidents_summary(db: DbSession, _: CurrentAnalyst) -> IncidentSummary:
    total, by_severity, by_category = read_with_retry(
        db, lambda: incident_service.get_active_summary(db)
    )
    return IncidentSummary(total_active=total, by_severity=by_severity, by_category=by_category)


@router.get("/{incident_id}", response_model=IncidentDetail, responses=problem_responses(404, 422))
def get_incident(incident_id: uuid.UUID, db: DbSession, _: CurrentAnalyst) -> IncidentDetail:
    return _detail(db, incident_id)


def _detail(db: DbSession, incident_id: uuid.UUID) -> IncidentDetail:
    found = read_with_retry(db, lambda: incident_service.get_incident(db, incident_id))
    if found is None:
        raise _not_found(incident_id)
    return IncidentDetail.from_parts(*found)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=IncidentDetail,
    responses=problem_responses(422, 429),
    dependencies=[Depends(limit_ingestion)],  # validates X-API-Key, then rate limits
    summary="Ingest an incident (trucks and integrations)",
    description="Authenticated with X-API-Key. Limited to 120 requests per minute per key.",
)
def create_incident(payload: IncidentCreate, db: DbSession, response: Response) -> IncidentDetail:
    incident_id = incident_service.create_incident(db, payload)
    response.headers["Location"] = router.url_path_for("get_incident", incident_id=incident_id)
    return _detail(db, incident_id)


@router.delete(
    "/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=problem_responses(404, 422),
    summary="Soft delete an incident",
)
def delete_incident(incident_id: uuid.UUID, analyst: CurrentAnalyst, db: DbSession) -> Response:
    if not incident_service.soft_delete_incident(db, incident_id, analyst.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Incident {incident_id} not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _not_found(incident_id: uuid.UUID) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Incident {incident_id} not found.")


def _conflict(db: DbSession, incident_id: uuid.UUID, sent_version: int) -> ProblemException:
    found = read_with_retry(db, lambda: incident_service.get_incident(db, incident_id))
    if found is None:  # deleted in the meantime
        return ProblemException(status.HTTP_404_NOT_FOUND, f"Incident {incident_id} not found.")
    current = IncidentDetail.from_parts(*found)
    return ProblemException(
        status.HTTP_409_CONFLICT,
        f"Incident was changed by someone else: version {sent_version} is outdated "
        f"(current: {current.version}). Review the current state and try again.",
        current=current,
    )


@router.patch(
    "/{incident_id}/status",
    response_model=IncidentDetail,
    responses=problem_responses(403, 404, 409, 422),
    summary="Change the status of an incident (optimistic locking)",
)
def change_incident_status(
    incident_id: uuid.UUID, payload: StatusChange, analyst: CurrentAnalyst, db: DbSession
) -> IncidentDetail:
    try:
        incident_status.change_status(
            db,
            incident_id,
            target=payload.status,
            version=payload.version,
            analyst_id=analyst.id,
            note=payload.note,
        )
    except incident_status.IncidentNotFound:
        raise _not_found(incident_id) from None
    except incident_status.VersionConflict:
        raise _conflict(db, incident_id, payload.version) from None
    except incident_status.NotResponsible as exc:
        assignee = exc.current.assignee
        name = assignee.name if assignee else "another analyst"
        raise ProblemException(
            status.HTTP_403_FORBIDDEN,
            f"Only the analyst responsible for this incident ({name}) can change its status.",
            assignee=AnalystRef.model_validate(assignee) if assignee else None,
        ) from None
    except incident_status.InvalidTransition as exc:
        allowed = [
            target.value
            for target, sources in incident_status.TRANSITION_SOURCES.items()
            if exc.from_status in sources
        ]
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Cannot change status from {exc.from_status.value} to {exc.to_status.value}. "
            f"Allowed from {exc.from_status.value}: {', '.join(allowed)}.",
        ) from None

    return _detail(db, incident_id)


@router.patch(
    "/{incident_id}",
    response_model=IncidentDetail,
    responses=problem_responses(404, 409, 422),
    summary="Edit an incident (optimistic locking)",
)
def update_incident(
    incident_id: uuid.UUID, payload: IncidentUpdate, analyst: CurrentAnalyst, db: DbSession
) -> IncidentDetail:
    try:
        incident_update.update_incident(db, incident_id, payload, analyst.id)
    except incident_status.IncidentNotFound:
        raise _not_found(incident_id) from None
    except incident_status.VersionConflict:
        raise _conflict(db, incident_id, payload.version) from None
    except incident_update.IncidentNotEditable as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"A {exc.status.value} incident cannot be edited. Reopen it first.",
        ) from None

    return _detail(db, incident_id)
