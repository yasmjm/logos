from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import CargoType, ClientTier, MessageDirection

# WhatsApp ids are the number in international format, digits only (e.g. 5511990001001).
Phone = Annotated[str, StringConstraints(pattern=r"^\d{10,15}$")]


class WhatsAppText(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class WhatsAppInbound(BaseModel):
    """One message object from the WhatsApp Cloud API webhook, without the envelope
    (entry[].changes[].value.messages[]); only text messages are handled (ADR 0005)."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "from": "5511990001001",
                    "id": "wamid.HBgNNTUxMTk5MDAwMTAwMRUCABIYFjNFQjBDMEZCMzM0",
                    "type": "text",
                    "text": {"body": "TRK-1001"},
                }
            ]
        },
    )

    from_: Phone = Field(alias="from")
    id: str | None = Field(default=None, max_length=128, description="Meta message id (wamid).")
    type: str = "text"
    text: WhatsAppText


class BotReply(BaseModel):
    replies: list[str] = Field(description="What the bot answered (also stored).")


class SimulatorMessage(BaseModel):
    """Message typed in the demo driver simulator."""

    phone: Phone
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ConversationMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    direction: MessageDirection
    text: str
    created_at: datetime


class ConversationThread(BaseModel):
    step: str | None = Field(description="Current triage step; null when no conversation is open.")
    options: list[str] = Field(description="Quick replies for the current step.")
    messages: list[ConversationMessageOut]


class FleetTruck(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    cargo_type: CargoType
    client_name: str
    client_tier: ClientTier


class RecentConversationOut(BaseModel):
    phone: str
    truck_code: str | None = Field(description="Truck the driver gave last; null if not yet.")
    last_message_at: datetime
    last_out_at: datetime | None = Field(description="Last message sent to the driver.")


class ConversationRef(BaseModel):
    phone: str
