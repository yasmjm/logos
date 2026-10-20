from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.models import IncidentStatus

INCONCLUSIVE_NOTE_MIN_LENGTH = 10


class StatusChange(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"status": "investigating", "version": 1},
                {
                    "status": "inconclusive",
                    "version": 2,
                    "note": "Motorista não atendeu e o rastreador está offline.",
                },
            ]
        },
    )

    status: IncidentStatus
    version: Annotated[int, Field(ge=1, description="The version the client last saw.")]
    note: Annotated[
        str | None,
        Field(
            default=None,
            max_length=2000,
            validate_default=True,
            description=(
                f"Reason for the change; required (at least {INCONCLUSIVE_NOTE_MIN_LENGTH} "
                "characters) for inconclusive."
            ),
        ),
    ]

    @field_validator("note")
    @classmethod
    def _note_rules(cls, note: str | None, info: ValidationInfo) -> str | None:
        note = note or None  # blank (after stripping) means no note
        if info.data.get("status") is IncidentStatus.INCONCLUSIVE and (
            note is None or len(note) < INCONCLUSIVE_NOTE_MIN_LENGTH
        ):
            raise ValueError(
                f"a note of at least {INCONCLUSIVE_NOTE_MIN_LENGTH} characters explaining why "
                "is required to mark an incident as inconclusive"
            )
        return note
