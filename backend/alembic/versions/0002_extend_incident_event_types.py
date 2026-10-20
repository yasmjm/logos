"""add deleted/updated event types, nullable to_status/driver_name, fix CHECK names

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_EVENT_TYPES = ("created", "status_changed")
NEW_EVENT_TYPES = (*OLD_EVENT_TYPES, "deleted", "updated")

# 0001 passed names like "ck_incidents_status" to CheckConstraint, and the metadata
# naming convention prefixed them again ("ck_incidents_ck_incidents_status").
# Rename them to what the models expect. op.f() marks a name as final from now on.
CHECKS = {
    "incidents": ("category", "severity", "status", "source"),
    "incident_events": ("event_type", "from_status", "to_status"),
}


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _rename_checks(*, doubled_to_fixed: bool) -> None:
    for table, columns in CHECKS.items():
        for column in columns:
            fixed = f"ck_{table}_{column}"
            doubled = f"ck_{table}_{fixed}"
            old, new = (doubled, fixed) if doubled_to_fixed else (fixed, doubled)
            op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT "{old}" TO "{new}"')


def _replace_event_type_check(values: tuple[str, ...]) -> None:
    name = op.f("ck_incident_events_event_type")
    op.drop_constraint(name, "incident_events", type_="check")
    op.create_check_constraint(name, "incident_events", _in("event_type", values))


def upgrade() -> None:
    _rename_checks(doubled_to_fixed=True)
    _replace_event_type_check(NEW_EVENT_TYPES)
    # deleted/updated events do not change status, so they have no target status.
    op.alter_column("incident_events", "to_status", existing_type=sa.String(32), nullable=True)
    # Ingestion accepts incidents without a driver name.
    op.alter_column("incidents", "driver_name", existing_type=sa.String(120), nullable=True)


def downgrade() -> None:
    # Fails on purpose if deleted/updated events exist: audit history is never discarded.
    op.alter_column("incidents", "driver_name", existing_type=sa.String(120), nullable=False)
    op.alter_column("incident_events", "to_status", existing_type=sa.String(32), nullable=False)
    _replace_event_type_check(OLD_EVENT_TYPES)
    _rename_checks(doubled_to_fixed=False)
