"""Add transient extracted-image storage metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0002"
down_revision: str | None = "20260924_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("article_images", sa.Column("local_path", sa.Text()))
    op.add_column("article_images", sa.Column("mime_type", sa.String(100)))


def downgrade() -> None:
    op.drop_column("article_images", "mime_type")
    op.drop_column("article_images", "local_path")
