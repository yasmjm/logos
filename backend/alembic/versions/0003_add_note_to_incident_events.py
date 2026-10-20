"""add note to incident_events

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Free text attached to an event: the reason for inconclusive, or what an edit changed.
    op.add_column("incident_events", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("incident_events", "note")
