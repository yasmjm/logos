from collections import Counter

from app.models import IncidentCategory, Severity
from app.seed import SEVERITY_COUNTS, TEMPLATES, TEMPLATES_BY_SEVERITY


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
