"""fleet (trucks) and the cargo/client snapshot on incidents

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CARGO_TYPES = ("hazardous", "perishable", "high_value", "general", "empty")
CLIENT_TIERS = ("strategic", "priority", "standard")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    op.create_table(
        "trucks",
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("cargo_type", sa.String(32), nullable=False),
        sa.Column("client_name", sa.String(120), nullable=False),
        sa.Column("client_tier", sa.String(32), nullable=False),
        sa.CheckConstraint(_in("cargo_type", CARGO_TYPES), name=op.f("ck_trucks_cargo_type")),
        sa.CheckConstraint(_in("client_tier", CLIENT_TIERS), name=op.f("ck_trucks_client_tier")),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_trucks")),
    )

    # Existing incidents: no fleet data was known when they were created.
    op.add_column(
        "incidents",
        sa.Column("cargo_type", sa.String(32), server_default="general", nullable=False),
    )
    op.add_column("incidents", sa.Column("client_name", sa.String(120), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("client_tier", sa.String(32), server_default="standard", nullable=False),
    )
    op.add_column(
        "incidents",
        sa.Column("fleet_match", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_incidents_cargo_type"), "incidents", _in("cargo_type", CARGO_TYPES)
    )
    op.create_check_constraint(
        op.f("ck_incidents_client_tier"), "incidents", _in("client_tier", CLIENT_TIERS)
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_incidents_client_tier"), "incidents", type_="check")
    op.drop_constraint(op.f("ck_incidents_cargo_type"), "incidents", type_="check")
    op.drop_column("incidents", "fleet_match")
    op.drop_column("incidents", "client_tier")
    op.drop_column("incidents", "client_name")
    op.drop_column("incidents", "cargo_type")
    op.drop_table("trucks")
