"""Response-time rules, in one place. The API exposes them on GET /config, so the
frontend never hard-codes them."""

from app.models import Severity

# Time to react (be assumed) per severity, in minutes.
SLA_MINUTES: dict[Severity, int] = {
    Severity.HIGH: 5,
    Severity.MEDIUM: 15,
    Severity.LOW: 30,
}

# High severity, open and nobody on it for longer than this: escalate.
ESCALATION_MINUTES = 5
