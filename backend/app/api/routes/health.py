from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.responses import problem_responses
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

READY_STATEMENT_TIMEOUT_MS = 1000


@router.get(
    "/health", response_model=HealthResponse, summary="Liveness (never touches the database)"
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses=problem_responses(503),
    summary="Readiness: the database answers SELECT 1",
)
def ready(db: DbSession) -> HealthResponse:
    # Short cap, so a struggling database makes readiness fail fast instead of hanging.
    db.execute(text(f"SET LOCAL statement_timeout = {READY_STATEMENT_TIMEOUT_MS}"))
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ready")
