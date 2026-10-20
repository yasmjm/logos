import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.analyst import Analyst
from app.models.enums import IncidentEventType, IncidentStatus, string_enum


class IncidentEvent(Base):
    __tablename__ = "incident_events"
    __table_args__ = (
        Index("ix_incident_events_incident_id_created_at", "incident_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"))
    analyst_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysts.id", ondelete="RESTRICT")
    )
    event_type: Mapped[IncidentEventType] = mapped_column(
        string_enum(IncidentEventType, "event_type")
    )
    from_status: Mapped[IncidentStatus | None] = mapped_column(
        string_enum(IncidentStatus, "from_status")
    )
    # Null for events that do not change status (deleted, updated).
    to_status: Mapped[IncidentStatus | None] = mapped_column(
        string_enum(IncidentStatus, "to_status")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analyst: Mapped[Analyst | None] = relationship()
