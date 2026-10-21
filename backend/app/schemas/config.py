from pydantic import BaseModel

from app.models import Severity


class Features(BaseModel):
    demo: bool
    chaos: bool


class AppConfig(BaseModel):
    sla_minutes: dict[Severity, int]
    escalation_minutes: int
    features: Features
