import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.analyst import Analyst
from app.models.enums import (
    IncidentCategory,
    IncidentSource,
    IncidentStatus,
    Severity,
    string_enum,
)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[IncidentCategory] = mapped_column(
        string_enum(IncidentCategory, "category"), index=True
    )
    severity: Mapped[Severity] = mapped_column(string_enum(Severity, "severity"), index=True)
    status: Mapped[IncidentStatus] = mapped_column(
        string_enum(IncidentStatus, "status"),
        default=IncidentStatus.OPEN,
        server_default=IncidentStatus.OPEN.value,
        index=True,
    )
    truck_code: Mapped[str] = mapped_column(String(20))
    driver_name: Mapped[str | None] = mapped_column(String(120))
    # Location is optional: WhatsApp reports must never be rejected for lacking it.
    highway: Mapped[str | None] = mapped_column(String(10))
    km: Mapped[Decimal | None] = mapped_column(Numeric(7, 1))
    location_note: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[IncidentSource] = mapped_column(
        string_enum(IncidentSource, "source"),
        default=IncidentSource.API,
        server_default=IncidentSource.API.value,
    )
    raw_message: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("analysts.id"))
    # Optimistic locking: status changes do UPDATE ... WHERE id = :id AND version = :version.
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # First transition to investigating (MTTA). Never overwritten.
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set on closed/inconclusive, cleared on reopen (MTTR).
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Soft delete: audit history in incident_events must never be removed.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee: Mapped[Analyst | None] = relationship()
