from pydantic import BaseModel

from app.schemas.incident import IncidentOut


class DemoResetResponse(BaseModel):
    deleted: int  # previous incidents soft-deleted (history kept)
    created: int  # fresh demo incidents, timestamps relative to now


class DemoSimulateResponse(BaseModel):
    items: list[IncidentOut]
