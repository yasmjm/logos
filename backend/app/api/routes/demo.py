import random
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, DemoResetAnalyst, DemoSimulateAnalyst
from app.api.responses import problem_responses
from app.schemas.demo import DemoResetResponse, DemoSimulateResponse
from app.schemas.incident import IncidentOut
from app.services import demo as demo_service
from app.services import incidents as incident_service

# Only mounted when DEMO_MODE=true (otherwise /demo/* is a plain 404).
router = APIRouter(prefix="/demo", tags=["demo"], responses=problem_responses(401, 429, 503))

_rng = random.Random()


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    summary="Recreate the demo data relative to now (1 per minute, global)",
    description=(
        "Soft-deletes the visible incidents (history is kept, with a 'deleted' event "
        "naming you) and creates the 120-incident demo set with fresh timestamps."
    ),
)
def reset(db: DbSession, analyst: DemoResetAnalyst) -> DemoResetResponse:
    result = demo_service.reset_demo_data(db, analyst.id)
    return DemoResetResponse(deleted=result.deleted, created=result.created)


@router.post(
    "/simulate",
    status_code=status.HTTP_201_CREATED,
    response_model=DemoSimulateResponse,
    responses=problem_responses(422),
    summary="Simulate incoming incidents (10 per minute per analyst)",
    description="Creates incidents from the demo templates through the ingestion service.",
)
def simulate(
    db: DbSession,
    _: DemoSimulateAnalyst,
    count: Annotated[int, Query(ge=1, le=10)] = 1,
) -> DemoSimulateResponse:
    ids = demo_service.simulate_incidents(db, count, _rng)
    found = [incident_service.get_incident(db, incident_id) for incident_id in ids]
    return DemoSimulateResponse(
        items=[IncidentOut.from_row(incident, score) for incident, score, _ in filter(None, found)]
    )
