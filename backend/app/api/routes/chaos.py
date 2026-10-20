from fastapi import APIRouter, Request

from app.api.deps import CurrentAnalyst
from app.api.responses import problem_responses
from app.core.chaos import ChaosController, ChaosSnapshot
from app.schemas.chaos import ChaosConfig, ChaosStatus

# Only mounted when CHAOS_ENABLED=true (otherwise /chaos is a plain 404).
router = APIRouter(prefix="/chaos", tags=["chaos"], responses=problem_responses(401))


def _controller(request: Request) -> ChaosController:
    return request.app.state.chaos


def _status(chaos: ChaosSnapshot) -> ChaosStatus:
    return ChaosStatus(
        latency_ms=chaos.latency_ms,
        failure_rate=chaos.failure_rate,
        active=chaos.active,
        expires_at=chaos.expires_at,
    )


@router.get("", response_model=ChaosStatus, summary="Current chaos settings")
def get_chaos(request: Request, _: CurrentAnalyst) -> ChaosStatus:
    return _status(_controller(request).snapshot())


@router.put(
    "",
    response_model=ChaosStatus,
    responses=problem_responses(422),
    summary="Inject latency and failures into /incidents (expires after 3 minutes)",
    description="Send latency_ms=0 and failure_rate=0 to turn chaos off immediately.",
)
def put_chaos(config: ChaosConfig, request: Request, _: CurrentAnalyst) -> ChaosStatus:
    return _status(_controller(request).configure(config.latency_ms, config.failure_rate))
