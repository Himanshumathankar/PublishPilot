"""Add editable WordPress article excerpt."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260925_0009"
down_revision: str | None = "20260924_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("excerpt", sa.Text()))


def downgrade() -> None:
    op.drop_column("articles", "excerpt")
