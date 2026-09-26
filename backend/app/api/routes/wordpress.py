import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.article import WordPressSite
from app.services.integrations import decrypt_secret
from app.services.wordpress import WordPressService

router = APIRouter()


async def configured_wordpress(db: AsyncSession, site_id: uuid.UUID) -> WordPressService:
    site = await db.get(WordPressSite, site_id)
    if not site or not site.active:
        from app.services.errors import ServiceError

        raise ServiceError("WORDPRESS_SITE_NOT_FOUND", "Select a valid publishing website.", 404)
    return WordPressService(
        site.base_url,
        site.username,
        decrypt_secret(site.application_password_encrypted),
        site.rank_math_endpoint,
    )


@router.get("/status")
async def wordpress_status(
    site_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    service = await configured_wordpress(db, site_id)
    await service.request("GET", "/wp-json/wp/v2/users/me")
    return {"connected": True}


@router.get("/categories")
async def wordpress_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: uuid.UUID,
) -> list[dict]:
    return await (await configured_wordpress(db, site_id)).categories()


@router.get("/authors")
async def wordpress_authors(
    db: Annotated[AsyncSession, Depends(get_db)], site_id: uuid.UUID
) -> list[dict]:
    return await (await configured_wordpress(db, site_id)).authors()
