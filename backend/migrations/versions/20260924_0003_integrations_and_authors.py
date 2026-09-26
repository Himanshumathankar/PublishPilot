"""Add encrypted integration settings and WordPress author selection."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0003"
down_revision: str | None = "20260924_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("author_id", sa.Integer()))
    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wordpress_base_url", sa.Text()),
        sa.Column("wordpress_username", sa.Text()),
        sa.Column("wordpress_application_password_encrypted", sa.Text()),
        sa.Column("rank_math_endpoint", sa.Text()),
        sa.Column("google_application_credentials", sa.Text()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("integration_settings")
    op.drop_column("articles", "author_id")
