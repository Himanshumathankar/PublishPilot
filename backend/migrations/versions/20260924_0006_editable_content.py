"""Add an optional editor-authored HTML override."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0006"
down_revision: str | None = "20260924_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("edited_html", sa.Text()))


def downgrade() -> None:
    op.drop_column("articles", "edited_html")
