from enum import StrEnum

from sqlalchemy import Enum


class IncidentCategory(StrEnum):
    VEHICLE_ACCIDENT = "vehicle_accident"
    ACCIDENT_WITH_VICTIMS = "accident_with_victims"
    ADVERSE_WEATHER = "adverse_weather"
    MECHANICAL_FAILURE = "mechanical_failure"
    ROAD_BLOCKAGE = "road_blockage"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CLOSED = "closed"
    INCONCLUSIVE = "inconclusive"


class IncidentSource(StrEnum):
    API = "api"
    WHATSAPP = "whatsapp"


class IncidentEventType(StrEnum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"


def string_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Store a StrEnum as VARCHAR + CHECK constraint (no native Postgres ENUM type)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda cls: [member.value for member in cls],
        validate_strings=True,
    )
