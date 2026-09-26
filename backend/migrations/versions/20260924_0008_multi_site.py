"""Add multiple WordPress publishing sites."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924_0008"
down_revision: str | None = "20260924_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_SITE = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "wordpress_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False, unique=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("application_password_encrypted", sa.Text(), nullable=False),
        sa.Column("rank_math_endpoint", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.execute(
        sa.text(f"""INSERT INTO wordpress_sites (id,name,base_url,username,application_password_encrypted,rank_math_endpoint)
        SELECT '{LEGACY_SITE}', COALESCE(NULLIF(regexp_replace(wordpress_base_url, '^https?://(www\\.)?', ''), ''), 'WordPress'), wordpress_base_url, wordpress_username, wordpress_application_password_encrypted, rank_math_endpoint
        FROM integration_settings WHERE wordpress_base_url IS NOT NULL AND wordpress_username IS NOT NULL AND wordpress_application_password_encrypted IS NOT NULL""")
    )
    op.add_column(
        "articles",
        sa.Column(
            "wordpress_site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wordpress_sites.id")
        ),
    )
    op.add_column(
        "media_assets",
        sa.Column(
            "wordpress_site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wordpress_sites.id")
        ),
    )
    op.execute(
        sa.text(
            f"UPDATE articles SET wordpress_site_id='{LEGACY_SITE}' WHERE EXISTS (SELECT 1 FROM wordpress_sites WHERE id='{LEGACY_SITE}')"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE media_assets SET wordpress_site_id='{LEGACY_SITE}' WHERE EXISTS (SELECT 1 FROM wordpress_sites WHERE id='{LEGACY_SITE}')"
        )
    )
    op.drop_constraint("media_assets_content_hash_key", "media_assets", type_="unique")
    op.create_unique_constraint(
        "uq_media_site_hash", "media_assets", ["wordpress_site_id", "content_hash"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_media_site_hash", "media_assets", type_="unique")
    op.create_unique_constraint("media_assets_content_hash_key", "media_assets", ["content_hash"])
    op.drop_column("media_assets", "wordpress_site_id")
    op.drop_column("articles", "wordpress_site_id")
    op.drop_table("wordpress_sites")
