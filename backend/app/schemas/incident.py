import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict

from app.models import (
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentSource,
    IncidentStatus,
    Severity,
)


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


# Optional text that is always null (never "") when missing.
OptionalText = Annotated[str | None, BeforeValidator(_blank_to_none)]


class AnalystRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    category: IncidentCategory
    severity: Severity
    status: IncidentStatus
    truck_code: str
    driver_name: str
    highway: OptionalText
    km: float | None
    location_note: OptionalText
    source: IncidentSource
    raw_message: OptionalText
    assignee: AnalystRef | None
    version: int
    created_at: datetime
    updated_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    priority_score: int

    @classmethod
    def from_row(cls, incident: Incident, priority_score: int) -> Self:
        data = IncidentOut.model_fields.keys() - {"priority_score"}
        return cls.model_validate(
            {field: getattr(incident, field) for field in data} | {"priority_score": priority_score}
        )


class IncidentListResponse(BaseModel):
    items: list[IncidentOut]
    total: int
    limit: int
    offset: int


class IncidentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: IncidentEventType
    from_status: IncidentStatus | None
    to_status: IncidentStatus
    analyst: AnalystRef | None
    created_at: datetime


class IncidentDetail(IncidentOut):
    events: list[IncidentEventOut]

    @classmethod
    def from_parts(
        cls, incident: Incident, priority_score: int, events: list[IncidentEvent]
    ) -> Self:
        base = IncidentOut.from_row(incident, priority_score)
        return cls.model_validate(
            base.model_dump()
            | {"events": [IncidentEventOut.model_validate(event) for event in events]}
        )


class IncidentSummary(BaseModel):
    total_active: int
    by_severity: dict[Severity, int]
    by_category: dict[IncidentCategory, int]
