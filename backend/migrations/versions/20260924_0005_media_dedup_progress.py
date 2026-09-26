"""Add global media deduplication and publish progress."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924_0005"
down_revision: str | None = "20260924_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("publish_logs", sa.Column("progress", postgresql.JSONB()))
    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("wordpress_media_id", sa.Integer(), nullable=False),
        sa.Column("wordpress_url", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_media_assets_content_hash", "media_assets", ["content_hash"])
    op.create_index("ix_media_assets_wordpress_media_id", "media_assets", ["wordpress_media_id"])


def downgrade() -> None:
    op.drop_index("ix_media_assets_wordpress_media_id", table_name="media_assets")
    op.drop_index("ix_media_assets_content_hash", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_column("publish_logs", "progress")
