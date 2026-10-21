from fastapi import APIRouter, Depends

from app.api.deps import DbSession, limit_ingestion
from app.api.responses import problem_responses
from app.schemas.whatsapp import BotReply, WhatsAppInbound
from app.services import whatsapp as whatsapp_service

router = APIRouter(
    prefix="/channels", tags=["channels"], responses=problem_responses(401, 422, 429, 503)
)


@router.post(
    "/whatsapp/webhook",
    response_model=BotReply,
    dependencies=[Depends(limit_ingestion)],  # same X-API-Key as ingestion
    summary="Receive a driver's WhatsApp message (triage bot)",
    description=(
        "Simplified WhatsApp Cloud API message object. The bot answers step by step and, "
        "at the end, creates the incident through the ingestion service (source=whatsapp). "
        "Non-text messages get a polite request for text."
    ),
)
def whatsapp_webhook(payload: WhatsAppInbound, db: DbSession) -> BotReply:
    if payload.type != "text":
        return BotReply(replies=["Por enquanto eu só entendo mensagens de texto."])
    return BotReply(replies=whatsapp_service.receive(db, payload.from_, payload.text.body))
