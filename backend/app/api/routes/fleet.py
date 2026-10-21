from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentAnalyst, DbSession
from app.api.responses import problem_responses
from app.models import Truck
from app.schemas.whatsapp import FleetTruck

router = APIRouter(prefix="/fleet", tags=["fleet"], responses=problem_responses(401, 503))


@router.get(
    "",
    response_model=list[FleetTruck],
    summary="The fleet: truck codes with their current cargo and client",
)
def list_fleet(db: DbSession, _: CurrentAnalyst) -> list[FleetTruck]:
    return [FleetTruck.model_validate(t) for t in db.scalars(select(Truck).order_by(Truck.code))]
