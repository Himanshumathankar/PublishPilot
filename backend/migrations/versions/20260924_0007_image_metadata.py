"""Add editable image alternative text."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0007"
down_revision: str | None = "20260924_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("article_images", sa.Column("alt_text", sa.Text()))


def downgrade() -> None:
    op.drop_column("article_images", "alt_text")
