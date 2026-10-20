import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models import IncidentCategory, IncidentSource, Severity

_HIGHWAY_PATTERN = re.compile(r"^([A-Z]{2})[\s-]*(\d{3})$")
_KM_STEP = Decimal("0.1")
_KM_MIN = Decimal("0")
_KM_MAX = Decimal("9999.9")
_LOCATION_NOTE_MAX = 255


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _normalize_highway(value: object) -> str | None:
    """Return "BR-116" for inputs like "br-116", "BR 116" or "BR116"; None if not a highway."""
    if not isinstance(value, str):
        return None
    match = _HIGHWAY_PATTERN.match(value.strip().upper())
    return f"{match[1]}-{match[2]}" if match else None


def _normalize_km(value: object) -> Decimal | None:
    """Round to one decimal place; None if not a number within 0 to 9999.9."""
    if isinstance(value, bool) or not isinstance(value, int | float | str | Decimal):
        return None
    try:
        # Accept the Brazilian decimal comma ("15,5") common in messages from drivers.
        text = str(value).strip().replace(",", ".")
        km = Decimal(text).quantize(_KM_STEP, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
    return km if _KM_MIN <= km <= _KM_MAX else None


def _clip(text: str, max_length: int) -> str:
    return text if len(text) <= max_length else text[: max_length - 1] + "…"


def salvage_location(data: dict[str, Any]) -> dict[str, Any]:
    """Location data never rejects an incident.

    A highway or km that cannot be used is stored as null, and the original value is
    appended to location_note (never overwriting what the sender wrote there).
    """
    notes: list[str] = []

    highway = _blank_to_none(data.get("highway"))
    if "highway" in data:
        data["highway"] = None
    if highway is not None:
        data["highway"] = _normalize_highway(highway)
        if data["highway"] is None:
            notes.append(f"Rodovia informada: {_clip(str(highway).strip(), 80)}")

    km = _blank_to_none(data.get("km"))
    if "km" in data:
        data["km"] = None
    if km is not None:
        data["km"] = _normalize_km(km)
        if data["km"] is None:
            notes.append(f"Km informado: {_clip(str(km).strip(), 40)}")

    note = _blank_to_none(data.get("location_note"))
    if note is not None and not isinstance(note, str):
        note = str(note)
    if not notes:
        if note is not None:
            data["location_note"] = _clip(note.strip(), _LOCATION_NOTE_MAX)
        return data

    # Keep the preserved originals intact; trim the sender's note if space runs out.
    suffix = " | ".join(notes)
    if note:
        room = _LOCATION_NOTE_MAX - len(suffix) - len(" | ")
        data["location_note"] = f"{_clip(note.strip(), room)} | {suffix}"
    else:
        data["location_note"] = suffix
    return data


def _optional_text(max_length: int) -> type:
    """Optional free text: blank becomes None; constraints apply only to real strings."""
    return Annotated[  # type: ignore[return-value]
        Annotated[str, StringConstraints(max_length=max_length)] | None,
        BeforeValidator(_blank_to_none),
    ]


DriverName = _optional_text(120)
LocationNote = _optional_text(_LOCATION_NOTE_MAX)
RawMessage = _optional_text(10_000)

# Highway and km are already normalized by salvage_location; the constraints below only
# document the contract and guard against regressions.
Highway = Annotated[
    Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}-\d{3}$")] | None,
    Field(
        description=(
            "Brazilian highway code, e.g. BR-116 or SP-330 (also accepts br116, BR 116). "
            "Unrecognized values are stored as null and kept in location_note."
        ),
        examples=["BR-116"],
    ),
]
Km = Annotated[
    Annotated[Decimal, Field(ge=_KM_MIN, le=_KM_MAX)] | None,
    Field(
        description=(
            "Kilometer marker, rounded to one decimal place. Values outside 0 to 9999.9 "
            "are stored as null and kept in location_note."
        ),
    ),
]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "category": "mechanical_failure",
                    "severity": "medium",
                    "description": "Superaquecimento do motor; caminhão parado no acostamento.",
                    "truck_code": "TRK-0420",
                    "driver_name": "João Silva",
                    "highway": "BR-116",
                    "km": 231.5,
                    "location_note": "Registro/SP",
                }
            ]
        },
    )

    category: IncidentCategory
    severity: Severity
    description: Annotated[str, StringConstraints(min_length=5, max_length=2000)]
    truck_code: Annotated[str, StringConstraints(min_length=1, max_length=20)]
    driver_name: DriverName = None
    highway: Highway = None
    km: Km = None
    location_note: LocationNote = None
    source: IncidentSource = IncidentSource.API
    raw_message: RawMessage = None

    @model_validator(mode="before")
    @classmethod
    def _salvage_location(cls, data: Any) -> Any:
        return salvage_location(dict(data)) if isinstance(data, dict) else data
