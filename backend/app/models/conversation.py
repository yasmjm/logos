import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import string_enum


class MessageDirection(StrEnum):
    IN = "in"  # from the driver
    OUT = "out"  # from the bot or the central


class Conversation(Base):
    """A WhatsApp triage conversation. `step` is null once it ended (incident created
    or cancelled); a conversation idle for 30 minutes also starts over."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_phone_updated_at", "phone", "updated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(20))
    step: Mapped[str | None] = mapped_column(String(32))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["ConversationMessage"]] = relationship(
        order_by="ConversationMessage.created_at", back_populates="conversation"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index(
            "ix_conversation_messages_conversation_id_created_at", "conversation_id", "created_at"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    direction: Mapped[MessageDirection] = mapped_column(string_enum(MessageDirection, "direction"))
    text: Mapped[str] = mapped_column(Text)
    # clock_timestamp, not now(): the bot's replies share the driver's transaction
    # and must still sort after the message they answer.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
