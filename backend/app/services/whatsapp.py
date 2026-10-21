"""WhatsApp channel: runs the triage bot (app/domain/triage.py) over stored
conversations and creates the incident through the ingestion service."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import triage
from app.models import (
    Analyst,
    Conversation,
    ConversationMessage,
    Incident,
    IncidentSource,
    IncidentStatus,
    MessageDirection,
)
from app.schemas.incident_create import IncidentCreate
from app.services.incidents import create_incident

IDLE_RESTART = timedelta(minutes=30)
IN, OUT = MessageDirection.IN, MessageDirection.OUT


def protocol(incident_id: uuid.UUID) -> str:
    """Short code the driver can quote to the central."""
    return incident_id.hex[:8].upper()


@dataclass
class Thread:
    step: str | None
    options: list[str]
    messages: list[ConversationMessage]


def _active_conversation(db: Session, phone: str, now: datetime) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .where(
            Conversation.phone == phone,
            Conversation.step.is_not(None),
            Conversation.updated_at > now - IDLE_RESTART,
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
        .with_for_update()
    )


def _say(db: Session, conversation: Conversation, direction: MessageDirection, text: str) -> None:
    db.add(ConversationMessage(conversation_id=conversation.id, direction=direction, text=text))


def _transcript(conversation: Conversation) -> str:
    return "\n".join(
        f"{'Motorista' if m.direction is IN else 'Bot'}: {m.text}" for m in conversation.messages
    )


def receive(db: Session, phone: str, text: str) -> list[str]:
    """Handle one message from the driver; returns the bot's replies (also stored)."""
    now = db.scalar(select(func.now()))
    conversation = _active_conversation(db, phone, now)
    if conversation is None:
        # First message, or the previous conversation ended or went idle: start over.
        conversation = Conversation(id=uuid.uuid4(), phone=phone, data={})
        db.add(conversation)
        db.flush()
        _say(db, conversation, IN, text)
        turn = triage.start()
    else:
        _say(db, conversation, IN, text)
        turn = triage.advance(triage.Step(conversation.step), conversation.data, text)

    replies = turn.replies
    if turn.completed:
        db.flush()
        db.refresh(conversation, ["messages"])
        incident_id = _create_incident(db, conversation, turn.data)
        conversation.incident_id = incident_id
        replies = [
            f"Pronto! Seu chamado foi registrado com o protocolo {protocol(incident_id)}. "
            "A central já recebeu e vai acompanhar por aqui."
        ]

    conversation.step = turn.step.value if turn.step else None
    conversation.data = turn.data
    conversation.updated_at = now
    for reply in replies:
        _say(db, conversation, OUT, reply)
    db.commit()
    return replies


def _create_incident(db: Session, conversation: Conversation, data: dict) -> uuid.UUID:
    category, severity = triage.classify(data)
    truck_code = data["truck"]
    return create_incident(
        db,
        IncidentCreate(
            category=category,
            severity=severity,
            description=triage.description(data),
            truck_code=truck_code,
            # The phone stays in the conversation only.
            driver_name=f"Motorista do {truck_code} (via WhatsApp)",
            source=IncidentSource.WHATSAPP,
            raw_message=_transcript(conversation),
            **triage.location_fields(data.get("location")),
        ),
    )


def thread(db: Session, phone: str) -> Thread:
    """Every message exchanged with this phone, plus the quick replies for the current step."""
    now = db.scalar(select(func.now()))
    messages = list(
        db.scalars(
            select(ConversationMessage)
            .join(Conversation)
            .where(Conversation.phone == phone)
            .order_by(ConversationMessage.created_at, ConversationMessage.id)
        )
    )
    active = db.scalar(
        select(Conversation.step)
        .where(
            Conversation.phone == phone,
            Conversation.step.is_not(None),
            Conversation.updated_at > now - IDLE_RESTART,
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    options = triage.OPTIONS.get(triage.Step(active), []) if active else []
    return Thread(step=active, options=options, messages=messages)


def notify_driver(
    db: Session, incident_id: uuid.UUID, target: IncidentStatus, analyst_id: uuid.UUID
) -> None:
    """Tell the driver when the central takes or closes a WhatsApp incident.
    Runs inside the status change transaction (the caller commits)."""
    if target not in (
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED,
        IncidentStatus.INCONCLUSIVE,
    ):
        return
    conversation = db.scalar(
        select(Conversation)
        .join(Incident, Incident.id == Conversation.incident_id)
        .where(Incident.id == incident_id, Incident.source == IncidentSource.WHATSAPP)
    )
    if conversation is None:
        return
    code = protocol(incident_id)
    if target is IncidentStatus.INVESTIGATING:
        name = db.scalar(select(Analyst.name).where(Analyst.id == analyst_id))
        text = f"{name} está cuidando do seu chamado {code}."
    else:
        text = f"Seu chamado {code} foi encerrado. Obrigado por avisar a central."
    _say(db, conversation, OUT, text)
