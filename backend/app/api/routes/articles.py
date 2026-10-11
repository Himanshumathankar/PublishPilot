import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models.article import (
    Article,
    ArticleImage,
    ArticleJob,
    ArticleStatus,
    MediaAsset,
    PublishLog,
    SourceType,
    WordPressSite,
)
from app.schemas.article import ArticleDocument
from app.services.docx_parser import parse_docx, validate_docx_archive
from app.services.editor import render_editor_html, sanitize_editor_html
from app.services.errors import ServiceError
from app.services.filenames import media_title, slugify_filename, slugify_slug
from app.services.google_docs import GoogleDocsService
from app.services.google_sheets import GoogleSheetsService
from app.services.images import convert_to_webp
from app.services.integrations import decrypt_secret, integration_settings
from app.services.renderer import render_article
from app.services.storage import ArticleStorage
from app.services.wordpress import WordPressService

router = APIRouter()
storage = ArticleStorage()
logger = structlog.get_logger()


class GoogleSourceRequest(BaseModel):
    url: HttpUrl


class ArticleMetadataUpdate(BaseModel):
    title: str
    meta_title: str
    meta_description: str
    excerpt: str = ""
    slug: str
    content_html: str | None = None


class ArticleImageUpdate(BaseModel):
    filename: str
    caption: str | None = None
    alt_text: str | None = None


async def _persist_import(
    db: AsyncSession,
    job: ArticleJob,
    document: ArticleDocument,
    extracted_images: list,
) -> dict:
    media_limit = get_settings().wordpress_media_max_mb * 1024 * 1024 - 65536
    image_blocks = {block.image_id: block for block in document.blocks if block.type == "image"}
    for extracted in extracted_images:
        extracted.data, extracted.filename, extracted.mime_type = convert_to_webp(
            extracted.data, extracted.filename, media_limit
        )
        if extracted.key in image_blocks:
            image_blocks[extracted.key].filename = extracted.filename
    article = Article(
        job_id=job.id,
        title=document.title,
        meta_title=document.meta_title,
        meta_description=document.meta_description,
        excerpt=document.excerpt,
        slug=document.slug,
        content=document.model_dump(mode="json"),
    )
    db.add(article)
    await db.flush()
    for position, extracted in enumerate(extracted_images):
        image_id = uuid.uuid4()
        path = storage.save(article.id, image_id, extracted.filename, extracted.data)
        db.add(
            ArticleImage(
                id=image_id,
                article_id=article.id,
                position=position,
                original_filename=extracted.original_filename,
                generated_filename=extracted.filename,
                caption=extracted.caption,
                figure_number=extracted.figure_number,
                local_path=path,
                mime_type=extracted.mime_type,
            )
        )
    job.status = ArticleStatus.READY
    await db.commit()
    return {"id": str(article.id), "status": "ready"}


async def _wordpress(db: AsyncSession, site_id: uuid.UUID) -> WordPressService:
    site = await db.get(WordPressSite, site_id)
    if not site or not site.active:
        raise ServiceError("WORDPRESS_SITE_NOT_FOUND", "Select a valid publishing website.", 404)
    return WordPressService(
        site.base_url,
        site.username,
        decrypt_secret(site.application_password_encrypted),
        site.rank_math_endpoint,
    )


async def _publish_progress(
    db: AsyncSession, log: PublishLog, stage: str, status: str, message: str
) -> None:
    event = {
        "stage": stage,
        "status": status,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log.progress = [*(log.progress or []), event]
    await db.commit()


async def _media_asset(db: AsyncSession, site_id: uuid.UUID, data: bytes) -> MediaAsset | None:
    digest = hashlib.sha256(data).hexdigest()
    return await db.scalar(
        select(MediaAsset).where(
            MediaAsset.wordpress_site_id == site_id, MediaAsset.content_hash == digest
        )
    )


def _remember_media(
    site_id: uuid.UUID, data: bytes, media: dict, filename: str, mime_type: str
) -> MediaAsset:
    return MediaAsset(
        wordpress_site_id=site_id,
        content_hash=hashlib.sha256(data).hexdigest(),
        wordpress_media_id=media["id"],
        wordpress_url=media["source_url"],
        filename=filename,
        mime_type=mime_type,
    )


def _media_filename_matches(asset: MediaAsset, filename: str) -> bool:
    return Path(asset.filename).name.casefold() == Path(filename).name.casefold()


def _serialize(article: Article) -> dict:
    document = ArticleDocument.model_validate(article.content).model_dump()
    images = []
    for model, parsed in zip(
        article.images, [b for b in document["blocks"] if b["type"] == "image"], strict=False
    ):
        parsed["source"] = f"/articles/{article.id}/images/{model.id}"
        images.append(
            {
                "id": str(model.id),
                "filename": model.generated_filename,
                "caption": model.caption,
                "alt_text": model.alt_text,
                "source": parsed["source"],
            }
        )
    return {
        "id": str(article.id),
        "title": article.title,
        "meta_title": article.meta_title,
        "meta_description": article.meta_description,
        "excerpt": article.excerpt,
        "slug": article.slug,
        "blocks": document["blocks"],
        "edited_html": article.edited_html,
        "images": images,
        "category_id": article.category_id,
        "category_ids": article.category_ids
        or ([article.category_id] if article.category_id else []),
        "author_id": article.author_id,
        "wordpress_site_id": str(article.wordpress_site_id) if article.wordpress_site_id else None,
        "wordpress_post_id": article.wordpress_post_id,
        "wordpress_url": article.wordpress_url,
        "status": article.job.status.value,
        "created_at": article.created_at.isoformat(),
    }


async def _article(db: AsyncSession, article_id: uuid.UUID) -> Article:
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.images), selectinload(Article.job))
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise ServiceError("ARTICLE_NOT_FOUND", "Article was not found.", 404)
    return article


@router.post("/process", status_code=201)
async def process_docx(
    file: Annotated[UploadFile, File()], db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    expected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if not file.filename or Path(file.filename).suffix.lower() != ".docx":
        raise ServiceError("INVALID_FILE_TYPE", "Only .docx files are accepted.")
    data = await file.read(get_settings().max_upload_size_mb * 1024 * 1024 + 1)
    if len(data) > get_settings().max_upload_size_mb * 1024 * 1024:
        raise ServiceError("FILE_TOO_LARGE", "The DOCX file exceeds the upload limit.", 413)
    if file.content_type not in (expected, "application/octet-stream") or not data.startswith(
        b"PK"
    ):
        raise ServiceError("INVALID_FILE_TYPE", "The uploaded file is not a valid DOCX.")
    validate_docx_archive(data, get_settings().max_docx_uncompressed_mb * 1024 * 1024)

    job = ArticleJob(source_type=SourceType.DOCX, source_name=Path(file.filename).name)
    db.add(job)
    await db.flush()
    try:
        parsed = parse_docx(data)
        return await _persist_import(db, job, parsed.article, parsed.images)
    except ServiceError as exc:
        job.status = ArticleStatus.FAILED
        job.error_code = exc.code
        job.error_message = exc.message
        await db.commit()
        logger.warning(
            "article_import_failed",
            job_id=str(job.id),
            source_type=job.source_type.value,
            error_code=exc.code,
        )
        raise


@router.post("/process-google-doc", status_code=201)
async def process_google_doc(
    request: GoogleSourceRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    source_url = str(request.url)
    job = ArticleJob(source_type=SourceType.GOOGLE_DOC, source_name=source_url)
    db.add(job)
    await db.flush()
    try:
        config = await integration_settings(db)
        document, images = await GoogleDocsService(
            config.google_application_credentials
        ).import_document(source_url)
        return await _persist_import(db, job, document, images)
    except ServiceError as exc:
        job.status = ArticleStatus.FAILED
        job.error_code = exc.code
        job.error_message = exc.message
        await db.commit()
        logger.warning(
            "article_import_failed",
            job_id=str(job.id),
            source_type=job.source_type.value,
            error_code=exc.code,
        )
        raise


@router.post("/process-google-sheet", status_code=201)
async def process_google_sheet(
    request: GoogleSourceRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    source_url = str(request.url)
    job = ArticleJob(source_type=SourceType.GOOGLE_SHEET, source_name=source_url)
    db.add(job)
    await db.flush()
    try:
        config = await integration_settings(db)
        document, images = await GoogleSheetsService(
            config.google_application_credentials
        ).import_spreadsheet(source_url)
        return await _persist_import(db, job, document, images)
    except ServiceError as exc:
        job.status = ArticleStatus.FAILED
        job.error_code = exc.code
        job.error_message = exc.message
        await db.commit()
        logger.warning(
            "article_import_failed",
            job_id=str(job.id),
            source_type=job.source_type.value,
            error_code=exc.code,
        )
        raise


@router.get("/history")
async def history(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: ArticleStatus | None = None,
    source_type: SourceType | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    filters = []
    if status:
        filters.append(ArticleJob.status == status)
    if source_type:
        filters.append(ArticleJob.source_type == source_type)
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(Article.title.ilike(term), ArticleJob.source_name.ilike(term)))

    base = select(ArticleJob).outerjoin(Article).where(*filters)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.options(selectinload(ArticleJob.article))
        .order_by(ArticleJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for job in result.scalars().unique():
        article = job.article
        items.append(
            {
                "job_id": str(job.id),
                "article_id": str(article.id) if article else None,
                "title": article.title if article else None,
                "source_type": job.source_type.value,
                "source_name": job.source_name,
                "status": job.status.value,
                "wordpress_post_id": article.wordpress_post_id if article else None,
                "wordpress_url": article.wordpress_url if article else None,
                "category_id": article.category_id if article else None,
                "category_ids": article.category_ids if article else None,
                "author_id": article.author_id if article else None,
                "error_code": job.error_code,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
                "published_at": article.published_at.isoformat()
                if article and article.published_at
                else None,
            }
        )
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


@router.get("/history/{job_id}")
async def history_detail(job_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    result = await db.execute(
        select(ArticleJob)
        .options(
            selectinload(ArticleJob.article).selectinload(Article.images),
            selectinload(ArticleJob.article).selectinload(Article.publish_logs),
        )
        .where(ArticleJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise ServiceError("HISTORY_RECORD_NOT_FOUND", "History record was not found.", 404)
    article = job.article
    return {
        "job_id": str(job.id),
        "article_id": str(article.id) if article else None,
        "title": article.title if article else None,
        "source_type": job.source_type.value,
        "source_name": job.source_name,
        "status": job.status.value,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "article": {
            "meta_title": article.meta_title,
            "meta_description": article.meta_description,
            "excerpt": article.excerpt,
            "slug": article.slug,
            "category_id": article.category_id,
            "category_ids": article.category_ids,
            "author_id": article.author_id,
            "wordpress_post_id": article.wordpress_post_id,
            "wordpress_url": article.wordpress_url,
            "featured_media_id": article.featured_media_id,
            "published_at": article.published_at.isoformat() if article.published_at else None,
        }
        if article
        else None,
        "images": [
            {
                "id": str(image.id),
                "filename": image.generated_filename,
                "caption": image.caption,
                "wordpress_media_id": image.wordpress_media_id,
                "wordpress_url": image.wordpress_url,
            }
            for image in (article.images if article else [])
        ],
        "publish_logs": [
            {
                "id": str(log.id),
                "requested_status": log.requested_status,
                "success": log.success,
                "wordpress_post_id": log.wordpress_post_id,
                "error_code": log.error_code,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
                "progress": log.progress or [],
            }
            for log in sorted(
                article.publish_logs if article else [],
                key=lambda item: item.created_at,
                reverse=True,
            )
        ],
    }


@router.get("/{article_id}")
async def get_article(article_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    return _serialize(await _article(db, article_id))


@router.patch("/{article_id}")
async def update_article_metadata(
    article_id: uuid.UUID,
    payload: ArticleMetadataUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    article = await _article(db, article_id)
    article.title = payload.title.strip()
    article.meta_title = payload.meta_title.strip()
    article.meta_description = payload.meta_description.strip()
    article.excerpt = payload.excerpt.strip() or None
    article.slug = slugify_slug(payload.slug)
    if payload.content_html is not None:
        article.edited_html = sanitize_editor_html(payload.content_html)
    content = dict(article.content)
    content.update(
        title=article.title,
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        excerpt=article.excerpt,
        slug=article.slug,
    )
    article.content = content
    await db.commit()
    return _serialize(article)


@router.get("/{article_id}/images/{image_id}")
async def get_image(
    article_id: uuid.UUID, image_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    result = await db.execute(
        select(ArticleImage).where(
            ArticleImage.id == image_id, ArticleImage.article_id == article_id
        )
    )
    image = result.scalar_one_or_none()
    if not image or not image.local_path:
        raise ServiceError("IMAGE_NOT_FOUND", "Image was not found.", 404)
    return Response(
        storage.read(image.local_path), media_type=image.mime_type or "application/octet-stream"
    )


@router.patch("/{article_id}/images/{image_id}")
async def update_image_metadata(
    article_id: uuid.UUID,
    image_id: uuid.UUID,
    payload: ArticleImageUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    article = await _article(db, article_id)
    image = next((item for item in article.images if item.id == image_id), None)
    if not image:
        raise ServiceError("IMAGE_NOT_FOUND", "Image was not found.", 404)
    image.generated_filename = slugify_filename(
        Path(payload.filename).stem, ".webp", f"image-{image.position + 1}"
    )
    image.caption = (payload.caption or "").strip() or None
    image.alt_text = (payload.alt_text or "").strip() or None
    content = dict(article.content)
    blocks = [dict(block) for block in content["blocks"]]
    image_blocks = [block for block in blocks if block["type"] == "image"]
    if image.position < len(image_blocks):
        image_blocks[image.position]["filename"] = image.generated_filename
        image_blocks[image.position]["caption"] = image.caption
    content["blocks"] = blocks
    article.content = content
    await db.commit()
    return {
        "id": str(image.id),
        "filename": image.generated_filename,
        "caption": image.caption,
        "alt_text": image.alt_text,
    }


@router.get("/{article_id}/publish-progress")
async def publish_progress(
    article_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    result = await db.execute(
        select(PublishLog)
        .where(PublishLog.article_id == article_id)
        .order_by(PublishLog.created_at.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()
    if not log:
        return {"active": False, "events": []}
    return {
        "active": not log.success and not log.error_code,
        "success": log.success,
        "error_code": log.error_code,
        "error_message": log.error_message,
        "events": log.progress or [],
    }


@router.post("/{article_id}/publish")
async def publish_article(
    article_id: uuid.UUID,
    site_id: Annotated[uuid.UUID, Form()],
    category_ids: Annotated[list[int], Form(min_length=1)],
    author_id: Annotated[int, Form(gt=0)],
    status: Annotated[Literal["draft", "publish"], Form()],
    featured_image: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    article = await _article(db, article_id)
    category_ids = list(dict.fromkeys(category_ids))
    if any(category_id <= 0 for category_id in category_ids):
        raise ServiceError("VALIDATION_ERROR", "Select valid WordPress categories.")
    missing = [
        name
        for name, value in (
            ("title", article.title),
            ("meta_title", article.meta_title),
            ("meta_description", article.meta_description),
            ("slug", article.slug),
            ("content", article.content.get("blocks")),
        )
        if not value
    ]
    if missing:
        raise ServiceError("VALIDATION_ERROR", f"Missing required fields: {', '.join(missing)}.")
    requested = "draft" if status == "draft" else "publish"
    log = PublishLog(
        article_id=article.id,
        requested_status=requested,
        success=False,
        progress=[],
    )
    db.add(log)
    await _publish_progress(db, log, "validation", "complete", "Article fields validated.")
    featured = await featured_image.read(get_settings().max_upload_size_mb * 1024 * 1024 + 1)
    if len(featured) > get_settings().max_upload_size_mb * 1024 * 1024:
        error = ServiceError(
            "FEATURED_IMAGE_TOO_LARGE", "The featured image exceeds the upload limit.", 413
        )
        log.error_code = error.code
        log.error_message = error.message
        await _publish_progress(db, log, "error", "failed", f"{error.code}: {error.message}")
        raise error
    media_limit = get_settings().wordpress_media_max_mb * 1024 * 1024 - 65536
    try:
        featured, _, mime = convert_to_webp(
            featured, featured_image.filename or "featured-image", media_limit
        )
    except ServiceError as exc:
        log.error_code = exc.code
        log.error_message = exc.message
        await _publish_progress(db, log, "error", "failed", f"{exc.code}: {exc.message}")
        raise
    extension = ".webp"
    await _publish_progress(
        db, log, "featured_image", "complete", "Featured image converted to WebP."
    )
    try:
        wordpress = await _wordpress(db, site_id)
        if article.wordpress_site_id and article.wordpress_site_id != site_id:
            article.wordpress_post_id = None
            article.wordpress_url = None
            article.featured_media_id = None
            for image in article.images:
                image.wordpress_media_id = None
                image.wordpress_url = None
        article.wordpress_site_id = site_id
        slug_matches = await wordpress.posts_by_slug(article.slug)
        conflicts = [post for post in slug_matches if post.get("id") != article.wordpress_post_id]
        if conflicts:
            conflict = conflicts[0]
            raise ServiceError(
                "WORDPRESS_SLUG_CONFLICT",
                f"WordPress post {conflict.get('id')} already uses slug '{article.slug}'. "
                f"Open {conflict.get('link')} or choose a different slug.",
                409,
            )
        await _publish_progress(db, log, "slug", "complete", "WordPress slug is available.")
        image_urls: dict[str, str] = {}
        image_blocks = [block for block in article.content["blocks"] if block["type"] == "image"]
        total_images = len(image_blocks)
        for index, (model, block) in enumerate(
            zip(article.images, image_blocks, strict=True), start=1
        ):
            if model.wordpress_media_id and model.wordpress_url:
                existing_asset = None
                if model.local_path:
                    known_data, known_name, known_mime = convert_to_webp(
                        storage.read(model.local_path), model.generated_filename, media_limit
                    )
                    existing_asset = await _media_asset(db, site_id, known_data)
                    if not existing_asset:
                        db.add(
                            MediaAsset(
                                wordpress_site_id=site_id,
                                content_hash=hashlib.sha256(known_data).hexdigest(),
                                wordpress_media_id=model.wordpress_media_id,
                                wordpress_url=model.wordpress_url,
                                filename=known_name,
                                mime_type=known_mime,
                            )
                        )
                    elif not _media_filename_matches(existing_asset, known_name):
                        model.wordpress_media_id = None
                        model.wordpress_url = None
                if model.wordpress_media_id and model.wordpress_url:
                    image_urls[block["image_id"]] = model.wordpress_url
                    await wordpress.update_media_metadata(
                        model.wordpress_media_id,
                        media_title(model.caption)
                        if model.caption
                        else Path(model.generated_filename).stem,
                        model.caption or "",
                        model.alt_text or "",
                    )
                    await _publish_progress(
                        db,
                        log,
                        "inline_images",
                        "reused",
                        f"Reused image {index} of {total_images}: {model.generated_filename}.",
                    )
                    continue
            if not model.local_path:
                raise ServiceError(
                    "IMAGE_EXTRACTION_ERROR", f"{model.generated_filename} is unavailable."
                )
            image_data = storage.read(model.local_path)
            image_data, model.generated_filename, model.mime_type = convert_to_webp(
                image_data, model.generated_filename, media_limit
            )
            existing = await _media_asset(db, site_id, image_data)
            if existing and _media_filename_matches(existing, model.generated_filename):
                model.wordpress_media_id = existing.wordpress_media_id
                model.wordpress_url = existing.wordpress_url
                action = "reused"
            else:
                media = await wordpress.upload_media(
                    image_data,
                    model.generated_filename,
                    model.mime_type,
                    media_title(model.caption)
                    if model.caption
                    else Path(model.generated_filename).stem,
                    model.caption or "",
                    model.alt_text or "",
                )
                model.wordpress_media_id = media["id"]
                model.wordpress_url = media["source_url"]
                if existing:
                    existing.wordpress_media_id = media["id"]
                    existing.wordpress_url = media["source_url"]
                    existing.filename = model.generated_filename
                    existing.mime_type = model.mime_type
                else:
                    db.add(
                        _remember_media(
                            site_id, image_data, media, model.generated_filename, model.mime_type
                        )
                    )
                action = "uploaded"
            image_urls[block["image_id"]] = model.wordpress_url
            if model.wordpress_media_id:
                await wordpress.update_media_metadata(
                    model.wordpress_media_id,
                    media_title(model.caption)
                    if model.caption
                    else Path(model.generated_filename).stem,
                    model.caption or "",
                    model.alt_text or "",
                )
            await _publish_progress(
                db,
                log,
                "inline_images",
                action,
                f"{action.title()} image {index} of {total_images}: {model.generated_filename}.",
            )
        featured_name = slugify_filename(article.title, extension, "featured-image")
        existing_featured = await _media_asset(db, site_id, featured)
        if existing_featured:
            featured_media = {
                "id": existing_featured.wordpress_media_id,
                "source_url": existing_featured.wordpress_url,
            }
            featured_action = "reused"
        else:
            featured_media = await wordpress.upload_media(
                featured, featured_name, mime, article.title
            )
            db.add(_remember_media(site_id, featured, featured_media, featured_name, mime))
            featured_action = "uploaded"
        await _publish_progress(
            db,
            log,
            "featured_image",
            featured_action,
            f"Featured image {featured_action}.",
        )
        document = ArticleDocument.model_validate(article.content)
        payload = {
            "title": article.title,
            "content": render_editor_html(article.edited_html, image_urls)
            if article.edited_html
            else render_article(document, image_urls),
            "excerpt": article.excerpt or "",
            "slug": article.slug,
            "status": requested,
            "categories": category_ids,
            "author": author_id,
            "featured_media": featured_media["id"],
        }
        if article.wordpress_post_id:
            await _publish_progress(
                db,
                log,
                "wordpress_post",
                "working",
                f"Updating existing WordPress post {article.wordpress_post_id}.",
            )
            post = await wordpress.update_post(article.wordpress_post_id, payload)
        else:
            await _publish_progress(
                db, log, "wordpress_post", "working", f"Creating WordPress {requested}."
            )
            post = await wordpress.create_post(payload)
        article.category_id = category_ids[0]
        article.category_ids = category_ids
        article.author_id = author_id
        article.featured_media_id = featured_media["id"]
        article.wordpress_post_id = post["id"]
        article.wordpress_url = post.get("link")
        log.wordpress_post_id = post["id"]
        await _publish_progress(db, log, "rank_math", "working", "Applying Rank Math metadata.")
        await wordpress.apply_rank_math(post["id"], article.meta_title, article.meta_description)
        await _publish_progress(db, log, "verification", "working", "Verifying the WordPress post.")
        await wordpress.verify_post(post["id"], payload)
        article.job.status = (
            ArticleStatus.DRAFT if requested == "draft" else ArticleStatus.PUBLISHED
        )
        article.published_at = datetime.now(UTC) if requested == "publish" else None
        log.success = True
        await _publish_progress(
            db, log, "complete", "complete", f"WordPress {requested} completed successfully."
        )
        return {
            "wordpress_post_id": post["id"],
            "wordpress_url": post.get("link"),
            "status": requested,
        }
    except ServiceError as exc:
        log.error_code = exc.code
        log.error_message = exc.message
        await _publish_progress(db, log, "error", "failed", f"{exc.code}: {exc.message}")
        logger.warning(
            "article_publish_failed",
            article_id=str(article.id),
            requested_status=requested,
            error_code=exc.code,
        )
        raise
