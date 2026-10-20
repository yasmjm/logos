from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    model_validator,
)

from app.models import IncidentCategory, Severity
from app.schemas.incident_create import LocationNote, salvage_highway_and_km

EDITABLE_FIELDS = ("severity", "category", "description", "highway", "km", "location_note")


class IncidentUpdate(BaseModel):
    """Partial edit. Omitted fields are kept; highway, km and location_note accept null."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"version": 3, "severity": "high", "highway": "BR-116"}]},
    )

    version: Annotated[int, Field(ge=1, description="The version the client last saw.")]
    # Required-if-present: omitted keeps the value, explicit null is rejected (422).
    severity: Severity = None  # type: ignore[assignment]
    category: IncidentCategory = None  # type: ignore[assignment]
    description: Annotated[str, StringConstraints(min_length=5, max_length=2000)] = None  # type: ignore[assignment]
    # Same rules as ingestion: unusable location is stored as null, never rejected.
    highway: Annotated[
        Any,
        Field(
            description="Brazilian highway code, e.g. BR-116. Unrecognized values become "
            "null and are kept in location_note.",
            json_schema_extra={"type": ["string", "null"]},
        ),
    ] = None
    km: Annotated[
        Any,
        Field(
            description="Kilometer marker, rounded to one decimal place. Values outside "
            "0 to 9999.9 become null and are kept in location_note.",
            json_schema_extra={"type": ["number", "string", "null"]},
        ),
    ] = None
    location_note: LocationNote = None

    # Original values preserved from an unusable highway/km ("Rodovia informada: ...").
    _location_notes: list[str] = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def _salvage_location(self) -> "IncidentUpdate":
        data = {f: getattr(self, f) for f in ("highway", "km") if f in self.model_fields_set}
        self._location_notes = salvage_highway_and_km(data)
        for field, value in data.items():
            object.__setattr__(self, field, value)
        return self

    def changes(self) -> dict[str, Any]:
        """Only the editable fields the client actually sent."""
        return {f: getattr(self, f) for f in EDITABLE_FIELDS if f in self.model_fields_set}

    @property
    def location_notes(self) -> list[str]:
        return self._location_notes
