"""manual incident source (registered by an analyst)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_source_check(sources: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_incidents_source"), "incidents", type_="check")
    values = ", ".join(repr(s) for s in sources)
    op.create_check_constraint(op.f("ck_incidents_source"), "incidents", f"source IN ({values})")


def upgrade() -> None:
    _replace_source_check(("api", "whatsapp", "manual"))


def downgrade() -> None:
    _replace_source_check(("api", "whatsapp"))
