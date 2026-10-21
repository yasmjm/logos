import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict

from app.models import (
    CargoType,
    ClientTier,
    Incident,
    IncidentCategory,
    IncidentEvent,
    IncidentEventType,
    IncidentSource,
    IncidentStatus,
    Severity,
)

if TYPE_CHECKING:
    from app.services.incidents import Priority


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


class PriorityBreakdown(BaseModel):
    """Why the incident has its priority_score (rules in app/domain/priority.py)."""

    cargo_points: int
    problem_points: int
    client_points: int
    base: float  # weighted mean of the three grades, 0 to 100
    wait_bonus: int
    victims: bool  # active incident with victims: fixed top score


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    category: IncidentCategory
    severity: Severity
    status: IncidentStatus
    truck_code: str
    driver_name: OptionalText
    highway: OptionalText
    km: float | None
    location_note: OptionalText
    source: IncidentSource
    raw_message: OptionalText
    cargo_type: CargoType
    client_name: OptionalText
    client_tier: ClientTier
    fleet_match: bool
    assignee: AnalystRef | None
    version: int
    created_at: datetime
    updated_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    priority_score: int
    priority_breakdown: PriorityBreakdown

    @classmethod
    def from_row(cls, incident: Incident, priority: "Priority") -> Self:
        data = IncidentOut.model_fields.keys() - {"priority_score", "priority_breakdown"}
        return cls.model_validate(
            {field: getattr(incident, field) for field in data}
            | {
                "priority_score": priority.score,
                "priority_breakdown": PriorityBreakdown(
                    cargo_points=priority.cargo_points,
                    problem_points=priority.problem_points,
                    client_points=priority.client_points,
                    base=priority.base,
                    wait_bonus=priority.wait_bonus,
                    victims=priority.victims,
                ),
            }
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
    to_status: IncidentStatus | None
    note: str | None
    analyst: AnalystRef | None
    created_at: datetime


class IncidentDetail(IncidentOut):
    events: list[IncidentEventOut]

    @classmethod
    def from_parts(
        cls, incident: Incident, priority: "Priority", events: list[IncidentEvent]
    ) -> Self:
        base = IncidentOut.from_row(incident, priority)
        return cls.model_validate(
            base.model_dump()
            | {"events": [IncidentEventOut.model_validate(event) for event in events]}
        )


class IncidentSummary(BaseModel):
    total_active: int
    by_severity: dict[Severity, int]
    by_category: dict[IncidentCategory, int]
