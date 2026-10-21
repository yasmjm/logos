import random
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentAnalyst, DbSession, DemoResetAnalyst, DemoSimulateAnalyst
from app.api.responses import problem_responses
from app.models import Truck
from app.schemas.demo import DemoResetResponse, DemoSimulateResponse
from app.schemas.incident import IncidentOut
from app.schemas.whatsapp import (
    BotReply,
    ConversationMessageOut,
    ConversationRef,
    ConversationThread,
    FleetTruck,
    Phone,
    RecentConversationOut,
    SimulatorMessage,
)
from app.services import demo as demo_service
from app.services import incidents as incident_service
from app.services import whatsapp as whatsapp_service

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
        items=[
            IncidentOut.from_row(incident, priority)
            for incident, priority, _ in filter(None, found)
        ]
    )


@router.post(
    "/whatsapp/messages",
    response_model=BotReply,
    responses=problem_responses(422),
    summary="Driver simulator: send a message as the driver",
    description="Same triage bot as POST /channels/whatsapp/webhook, authenticated by the analyst.",
)
def simulator_send(payload: SimulatorMessage, db: DbSession, _: CurrentAnalyst) -> BotReply:
    return BotReply(replies=whatsapp_service.receive(db, payload.phone, payload.text))


@router.get(
    "/whatsapp/conversations/{phone}/messages",
    response_model=ConversationThread,
    responses=problem_responses(422),
    summary="Driver simulator: the messages exchanged with a phone",
)
def simulator_messages(phone: Phone, db: DbSession, _: CurrentAnalyst) -> ConversationThread:
    thread = whatsapp_service.thread(db, phone)
    return ConversationThread(
        step=thread.step,
        options=thread.options,
        messages=[
            ConversationMessageOut(
                id=str(m.id), direction=m.direction, text=m.text, created_at=m.created_at
            )
            for m in thread.messages
        ],
    )


@router.get(
    "/fleet",
    response_model=list[FleetTruck],
    summary="Driver simulator: the demo fleet, to pick a truck",
)
def fleet(db: DbSession, _: CurrentAnalyst) -> list[FleetTruck]:
    return [FleetTruck.model_validate(t) for t in db.scalars(select(Truck).order_by(Truck.code))]


@router.get(
    "/whatsapp/conversations",
    response_model=list[RecentConversationOut],
    summary="Driver simulator: recent conversations (one per phone)",
)
def simulator_recent(db: DbSession, _: CurrentAnalyst) -> list[RecentConversationOut]:
    return [RecentConversationOut(**vars(c)) for c in whatsapp_service.recent_conversations(db)]


@router.get(
    "/whatsapp/incidents/{incident_id}/conversation",
    response_model=ConversationRef,
    responses=problem_responses(404, 422),
    summary="Driver simulator: the conversation that created an incident",
)
def simulator_incident_conversation(
    incident_id: uuid.UUID, db: DbSession, _: CurrentAnalyst
) -> ConversationRef:
    phone = whatsapp_service.phone_of_incident(db, incident_id)
    if phone is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No WhatsApp conversation for incident {incident_id}."
        )
    return ConversationRef(phone=phone)
