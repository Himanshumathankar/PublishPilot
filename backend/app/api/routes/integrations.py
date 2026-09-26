import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.article import WordPressSite
from app.services.integrations import encrypt_secret, integration_settings
from app.services.wordpress import WordPressService

router = APIRouter()


class WordPressCredentials(BaseModel):
    name: str = "WordPress"
    base_url: HttpUrl
    username: str
    application_password: str
    rank_math_endpoint: str | None = None


class ContentIntegrationSettings(BaseModel):
    rank_math_endpoint: str | None = None
    google_application_credentials: str | None = None


@router.get("")
async def get_integrations(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    config = await integration_settings(db)
    sites = (await db.scalars(select(WordPressSite).order_by(WordPressSite.name))).all()
    return {
        "wordpress_sites": [
            {
                "id": str(site.id),
                "name": site.name,
                "base_url": site.base_url,
                "username": site.username,
                "rank_math_endpoint": site.rank_math_endpoint,
                "active": site.active,
            }
            for site in sites
        ],
        "wordpress": {
            "configured": bool(
                config.wordpress_base_url
                and config.wordpress_username
                and config.wordpress_application_password_encrypted
            ),
            "base_url": config.wordpress_base_url,
            "username": config.wordpress_username,
        },
        "rank_math_endpoint": config.rank_math_endpoint,
        "google_application_credentials": config.google_application_credentials,
    }


@router.put("/wordpress")
async def save_wordpress(
    payload: WordPressCredentials, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    base_url = str(payload.base_url).rstrip("/")
    service = WordPressService(base_url, payload.username, payload.application_password)
    user = await service.request("GET", "/wp-json/wp/v2/users/me", params={"context": "edit"})
    config = await integration_settings(db)
    config.wordpress_base_url = base_url
    config.wordpress_username = payload.username
    config.wordpress_application_password_encrypted = encrypt_secret(payload.application_password)
    await db.commit()
    return {"connected": True, "user": user.get("name") if isinstance(user, dict) else None}


@router.post("/wordpress-sites", status_code=201)
async def create_wordpress_site(
    payload: WordPressCredentials, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    base_url = str(payload.base_url).rstrip("/")
    service = WordPressService(
        base_url, payload.username, payload.application_password, payload.rank_math_endpoint
    )
    user = await service.request("GET", "/wp-json/wp/v2/users/me", params={"context": "edit"})
    site = WordPressSite(
        name=payload.name.strip() or base_url,
        base_url=base_url,
        username=payload.username.strip(),
        application_password_encrypted=encrypt_secret(payload.application_password),
        rank_math_endpoint=(payload.rank_math_endpoint or "").strip() or None,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return {
        "id": str(site.id),
        "name": site.name,
        "base_url": site.base_url,
        "username": site.username,
        "connected_user": user.get("name") if isinstance(user, dict) else None,
    }


@router.delete("/wordpress-sites/{site_id}")
async def delete_wordpress_site(
    site_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    site = await db.get(WordPressSite, site_id)
    if not site:
        from app.services.errors import ServiceError

        raise ServiceError("WORDPRESS_SITE_NOT_FOUND", "Publishing website was not found.", 404)
    site.active = False
    await db.commit()
    return {"deleted": True}


@router.put("/content")
async def save_content_integrations(
    payload: ContentIntegrationSettings, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    google_path = (payload.google_application_credentials or "").strip() or None
    if google_path and (not Path(google_path).is_absolute() or ".." in Path(google_path).parts):
        from app.services.errors import ServiceError

        raise ServiceError(
            "INVALID_GOOGLE_CREDENTIAL_PATH", "Google credentials must use an absolute path."
        )
    config = await integration_settings(db)
    config.rank_math_endpoint = (payload.rank_math_endpoint or "").strip() or None
    config.google_application_credentials = google_path
    await db.commit()
    return {"saved": True}
