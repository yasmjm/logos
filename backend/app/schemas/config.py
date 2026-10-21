from pydantic import BaseModel

from app.models import CargoType, ClientTier, IncidentCategory, Severity


class Features(BaseModel):
    demo: bool
    chaos: bool


class PriorityRules(BaseModel):
    weights: dict[str, float]
    cargo_points: dict[CargoType, int]
    problem_points: dict[IncidentCategory, dict[Severity, int]]
    client_points: dict[ClientTier, int]
    wait_bonus_per_minute: int
    wait_bonus_cap: int
    victims_score: int


class AppConfig(BaseModel):
    sla_minutes: dict[Severity, int]
    escalation_minutes: int
    priority: PriorityRules
    features: Features
