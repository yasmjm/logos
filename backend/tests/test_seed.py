import random
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Incident, IncidentCategory, IncidentStatus, Severity
from app.seed import (
    SEVERITY_COUNTS,
    TEMPLATES,
    TEMPLATES_BY_SEVERITY,
    add_demo_incidents,
    ensure_analysts,
    random_incident_fields,
)
from app.services.metrics import compute_metrics


def test_each_category_has_at_least_eight_templates() -> None:
    per_category = Counter(template.category for template in TEMPLATES)

    assert all(per_category[category] >= 8 for category in IncidentCategory)


def test_every_seeded_severity_has_templates() -> None:
    assert all(TEMPLATES_BY_SEVERITY[severity] for severity in SEVERITY_COUNTS)


def test_descriptions_are_unique() -> None:
    descriptions = [template.description for template in TEMPLATES]

    assert len(descriptions) == len(set(descriptions))


def test_severity_is_coherent_with_obvious_descriptions() -> None:
    by_description = {t.description: t.severity for t in TEMPLATES}

    for description, severity in by_description.items():
        text = description.lower()
        if "ferimentos graves" in text or "presa às ferragens" in text or "desacordado" in text:
            assert severity is Severity.HIGH, description
        if "danos leves" in text or "viagem segue normalmente" in text:
            assert severity is Severity.LOW, description


def test_random_incident_fields_are_coherent_and_valid_for_ingestion() -> None:
    from app.schemas.incident_create import IncidentCreate

    rng = random.Random(1)
    by_description = {t.description: t for t in TEMPLATES}

    for _ in range(200):
        fields = random_incident_fields(rng)
        template = by_description[fields["description"]]
        assert (template.category, template.severity) == (fields["category"], fields["severity"])
        IncidentCreate(**fields)  # accepted by the same rules as the public ingestion


def test_random_severity_follows_seed_mix() -> None:
    rng = random.Random(3)
    counts = Counter(random_incident_fields(rng)["severity"] for _ in range(2000))

    assert 0.10 < counts[Severity.HIGH] / 2000 < 0.20
    assert 0.38 < counts[Severity.MEDIUM] / 2000 < 0.52


def test_ensure_analysts_keeps_existing_ids(db: Session) -> None:
    first = {a.username: a.id for a in ensure_analysts(db)}
    second = {a.username: a.id for a in ensure_analysts(db)}

    assert first == second
    assert set(first) == {"ana", "bruno"}


def test_demo_set_keeps_totals_and_a_readable_signal(db: Session) -> None:
    """Right after seeding, only a handful are past the SLA: the red stays meaningful."""
    add_demo_incidents(db, ensure_analysts(db), datetime.now(UTC))
    metrics = compute_metrics(db)

    assert 5 <= metrics.sla_breached_now <= 10
    assert 2 <= metrics.escalated_now <= 3
    assert metrics.mtta_seconds is not None and 60 <= metrics.mtta_seconds <= 12 * 60

    by_severity = dict(
        db.execute(select(Incident.severity, func.count()).group_by(Incident.severity)).all()
    )
    by_status = dict(
        db.execute(select(Incident.status, func.count()).group_by(Incident.status)).all()
    )
    assert by_severity == SEVERITY_COUNTS
    assert by_status == {
        IncidentStatus.OPEN: 85,
        IncidentStatus.INVESTIGATING: 20,
        IncidentStatus.CLOSED: 12,
        IncidentStatus.INCONCLUSIVE: 3,
    }
