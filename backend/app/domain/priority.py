"""Business-impact priority, in one place (see docs/adr/0005).

Score of an active incident = weighted mean of three 0-100 grades + waiting bonus:

    base  = (2 × cargo + 1.5 × problem + 1 × client) / 4.5     → 0 to 100
    score = round(base + wait bonus)                            → 0 to 120

The waiting bonus is 1 point per minute without an owner, capped at 20, frozen when
someone takes the incident (acknowledged_at). Active incidents with victims are
always above everything else (fixed score, outside the mean). Resolved incidents get
no bonus and go to the end of the queue. The weights are a hypothesis to be
validated with the client's operation.
"""

from app.models import CargoType, ClientTier, IncidentCategory, Severity

CARGO_POINTS: dict[CargoType, int] = {
    CargoType.HAZARDOUS: 100,
    CargoType.PERISHABLE: 90,
    CargoType.HIGH_VALUE: 75,
    CargoType.GENERAL: 40,
    CargoType.EMPTY: 10,
}

# Problem grade by category × severity.
PROBLEM_POINTS: dict[IncidentCategory, dict[Severity, int]] = {
    IncidentCategory.VEHICLE_ACCIDENT: {Severity.HIGH: 85, Severity.MEDIUM: 60, Severity.LOW: 35},
    IncidentCategory.ROAD_BLOCKAGE: {Severity.HIGH: 80, Severity.MEDIUM: 55, Severity.LOW: 30},
    IncidentCategory.ADVERSE_WEATHER: {Severity.HIGH: 70, Severity.MEDIUM: 45, Severity.LOW: 25},
    IncidentCategory.MECHANICAL_FAILURE: {Severity.HIGH: 65, Severity.MEDIUM: 45, Severity.LOW: 20},
}
# Victims are ranked by the fixed rule below while active; this grade only shows in
# the breakdown of a resolved incident with victims.
VICTIMS_PROBLEM_POINTS = 100

CLIENT_POINTS: dict[ClientTier, int] = {
    ClientTier.STRATEGIC: 100,
    ClientTier.PRIORITY: 70,
    ClientTier.STANDARD: 40,
}

WEIGHTS = {"cargo": 2.0, "problem": 1.5, "client": 1.0}
WEIGHT_TOTAL = sum(WEIGHTS.values())  # 4.5

WAIT_BONUS_PER_MINUTE = 1
WAIT_BONUS_CAP = 20

# Active incidents with victims: above every possible score (max is 100 + 20).
VICTIMS_SCORE = 200
