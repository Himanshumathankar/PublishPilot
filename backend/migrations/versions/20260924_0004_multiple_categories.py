"""Store multiple selected WordPress categories."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924_0004"
down_revision: str | None = "20260924_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("category_ids", postgresql.JSONB()))
    op.execute(
        "UPDATE articles SET category_ids = jsonb_build_array(category_id) "
        "WHERE category_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("articles", "category_ids")
