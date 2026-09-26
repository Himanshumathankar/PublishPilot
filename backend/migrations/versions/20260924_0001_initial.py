"""Create initial article publishing tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    article_status = postgresql.ENUM(
        "processing",
        "ready",
        "draft",
        "published",
        "failed",
        name="article_status",
        create_type=False,
    )
    source_type = postgresql.ENUM(
        "docx", "google_doc", "google_sheet", name="source_type", create_type=False
    )
    article_status.create(op.get_bind(), checkfirst=True)
    source_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "article_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_name", sa.String(2048), nullable=False),
        sa.Column("status", article_status, nullable=False, server_default="processing"),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_article_jobs_status", "article_jobs", ["status"])

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("article_jobs.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("meta_title", sa.Text()),
        sa.Column("meta_description", sa.Text()),
        sa.Column("slug", sa.String(255)),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("category_id", sa.Integer()),
        sa.Column("wordpress_post_id", sa.Integer()),
        sa.Column("wordpress_url", sa.Text()),
        sa.Column("featured_media_id", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_articles_wordpress_post_id", "articles", ["wordpress_post_id"])

    op.create_table(
        "article_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("generated_filename", sa.String(512), nullable=False),
        sa.Column("caption", sa.Text()),
        sa.Column("figure_number", sa.Integer()),
        sa.Column("wordpress_media_id", sa.Integer()),
        sa.Column("wordpress_url", sa.Text()),
        sa.UniqueConstraint("article_id", "position", name="uq_article_image_position"),
    )

    op.create_table(
        "publish_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_status", sa.String(20), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("wordpress_post_id", sa.Integer()),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("publish_logs")
    op.drop_table("article_images")
    op.drop_index("ix_articles_wordpress_post_id", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_article_jobs_status", table_name="article_jobs")
    op.drop_table("article_jobs")
    postgresql.ENUM(name="source_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="article_status").drop(op.get_bind(), checkfirst=True)
