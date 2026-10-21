from fastapi import APIRouter

from app.api.deps import AppSettings, CurrentAnalyst
from app.api.responses import problem_responses
from app.domain.sla import ESCALATION_MINUTES, SLA_MINUTES
from app.schemas.config import AppConfig, Features

# Outside /incidents on purpose: chaos mode never affects it.
router = APIRouter(tags=["config"], responses=problem_responses(401))


@router.get(
    "/config",
    response_model=AppConfig,
    summary="Business rules and available tools, for the frontend",
)
def get_config(settings: AppSettings, _: CurrentAnalyst) -> AppConfig:
    return AppConfig(
        sla_minutes=SLA_MINUTES,
        escalation_minutes=ESCALATION_MINUTES,
        features=Features(demo=settings.demo_mode, chaos=settings.chaos_enabled),
    )
