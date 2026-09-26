import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SourceType(StrEnum):
    DOCX = "docx"
    GOOGLE_DOC = "google_doc"
    GOOGLE_SHEET = "google_sheet"


class ArticleStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"


class ArticleJob(Base):
    __tablename__ = "article_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", values_callable=lambda e: [x.value for x in e])
    )
    source_name: Mapped[str] = mapped_column(String(2048))
    status: Mapped[ArticleStatus] = mapped_column(
        Enum(ArticleStatus, name="article_status", values_callable=lambda e: [x.value for x in e]),
        default=ArticleStatus.PROCESSING,
        index=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    article: Mapped["Article | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("article_jobs.id", ondelete="CASCADE"), unique=True
    )
    title: Mapped[str] = mapped_column(Text)
    meta_title: Mapped[str | None] = mapped_column(Text)
    meta_description: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    edited_html: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(Integer)
    category_ids: Mapped[list[int] | None] = mapped_column(JSONB)
    author_id: Mapped[int | None] = mapped_column(Integer)
    wordpress_site_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wordpress_sites.id"))
    wordpress_post_id: Mapped[int | None] = mapped_column(Integer, index=True)
    wordpress_url: Mapped[str | None] = mapped_column(Text)
    featured_media_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    job: Mapped[ArticleJob] = relationship(back_populates="article")
    images: Mapped[list["ArticleImage"]] = relationship(
        back_populates="article", cascade="all, delete-orphan", order_by="ArticleImage.position"
    )
    publish_logs: Mapped[list["PublishLog"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class ArticleImage(Base):
    __tablename__ = "article_images"
    __table_args__ = (UniqueConstraint("article_id", "position", name="uq_article_image_position"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(512))
    generated_filename: Mapped[str] = mapped_column(String(512))
    caption: Mapped[str | None] = mapped_column(Text)
    alt_text: Mapped[str | None] = mapped_column(Text)
    figure_number: Mapped[int | None] = mapped_column(Integer)
    wordpress_media_id: Mapped[int | None] = mapped_column(Integer)
    wordpress_url: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    article: Mapped[Article] = relationship(back_populates="images")


class PublishLog(Base):
    __tablename__ = "publish_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    requested_status: Mapped[str] = mapped_column(String(20))
    success: Mapped[bool] = mapped_column(Boolean)
    wordpress_post_id: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    article: Mapped[Article] = relationship(back_populates="publish_logs")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    __table_args__ = (
        UniqueConstraint("wordpress_site_id", "content_hash", name="uq_media_site_hash"),
    )
    wordpress_site_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wordpress_sites.id"))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    wordpress_media_id: Mapped[int] = mapped_column(Integer, index=True)
    wordpress_url: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IntegrationSettings(Base):
    __tablename__ = "integration_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    wordpress_base_url: Mapped[str | None] = mapped_column(Text)
    wordpress_username: Mapped[str | None] = mapped_column(Text)
    wordpress_application_password_encrypted: Mapped[str | None] = mapped_column(Text)
    rank_math_endpoint: Mapped[str | None] = mapped_column(Text)
    google_application_credentials: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WordPressSite(Base):
    __tablename__ = "wordpress_sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(Text, unique=True)
    username: Mapped[str] = mapped_column(Text)
    application_password_encrypted: Mapped[str] = mapped_column(Text)
    rank_math_endpoint: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
