"""create analysts, incidents and incident_events

Revision ID: 0001
Revises:
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = (
    "vehicle_accident",
    "accident_with_victims",
    "adverse_weather",
    "mechanical_failure",
    "road_blockage",
)
SEVERITIES = ("high", "medium", "low")
STATUSES = ("open", "investigating", "closed", "inconclusive")
SOURCES = ("api", "whatsapp")
EVENT_TYPES = ("created", "status_changed")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    op.create_table(
        "analysts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysts"),
        sa.UniqueConstraint("username", name="uq_analysts_username"),
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), server_default="open", nullable=False),
        sa.Column("truck_code", sa.String(20), nullable=False),
        sa.Column("driver_name", sa.String(120), nullable=False),
        sa.Column("highway", sa.String(10), nullable=True),
        sa.Column("km", sa.Numeric(7, 1), nullable=True),
        sa.Column("location_note", sa.String(255), nullable=True),
        sa.Column("source", sa.String(32), server_default="api", nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(_in("category", CATEGORIES), name="ck_incidents_category"),
        sa.CheckConstraint(_in("severity", SEVERITIES), name="ck_incidents_severity"),
        sa.CheckConstraint(_in("status", STATUSES), name="ck_incidents_status"),
        sa.CheckConstraint(_in("source", SOURCES), name="ck_incidents_source"),
        sa.ForeignKeyConstraint(
            ["assigned_to"], ["analysts.id"], name="fk_incidents_assigned_to_analysts"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_category", "incidents", ["category"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])

    op.create_table(
        "incident_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("analyst_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(_in("event_type", EVENT_TYPES), name="ck_incident_events_event_type"),
        sa.CheckConstraint(_in("from_status", STATUSES), name="ck_incident_events_from_status"),
        sa.CheckConstraint(_in("to_status", STATUSES), name="ck_incident_events_to_status"),
        # RESTRICT: audit history must never be deleted (incidents use soft delete).
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_incident_events_incident_id_incidents",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["analyst_id"],
            ["analysts.id"],
            name="fk_incident_events_analyst_id_analysts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incident_events"),
    )
    op.create_index(
        "ix_incident_events_incident_id_created_at",
        "incident_events",
        ["incident_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_events_incident_id_created_at", table_name="incident_events")
    op.drop_table("incident_events")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_index("ix_incidents_category", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_table("incidents")
    op.drop_table("analysts")
