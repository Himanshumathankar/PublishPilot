import base64
import hashlib
import hmac
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.errors import ServiceError

router = APIRouter()
COOKIE = "article_publisher_session"


class LoginRequest(BaseModel):
    username: str
    password: str


def _signature(payload: str) -> str:
    return hmac.new(
        get_settings().app_secret_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def _token(username: str) -> str:
    payload = f"{username}:{int(time.time()) + 60 * 60 * 12}"
    return base64.urlsafe_b64encode(f"{payload}:{_signature(payload)}".encode()).decode()


def require_user(
    article_publisher_session: Annotated[str | None, Cookie(alias=COOKIE)] = None,
) -> str:
    if not article_publisher_session:
        raise ServiceError("AUTH_REQUIRED", "Sign in to access PublishPilot.", 401)
    try:
        decoded = base64.urlsafe_b64decode(article_publisher_session.encode()).decode()
        username, expires, signature = decoded.rsplit(":", 2)
        payload = f"{username}:{expires}"
        valid = hmac.compare_digest(signature, _signature(payload)) and int(expires) > int(
            time.time()
        )
    except (ValueError, UnicodeError):
        valid = False
    if not valid:
        raise ServiceError("AUTH_REQUIRED", "Your session expired. Sign in again.", 401)
    return username


@router.post("/login")
async def login(payload: LoginRequest, response: Response) -> dict:
    settings = get_settings()
    if not (
        hmac.compare_digest(payload.username, settings.app_username)
        and hmac.compare_digest(payload.password, settings.app_password)
    ):
        raise ServiceError("INVALID_LOGIN", "Incorrect application username or password.", 401)
    response.set_cookie(
        COOKIE,
        _token(payload.username),
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=43200,
        path="/",
    )
    return {"authenticated": True, "username": payload.username}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE, path="/")
    return {"authenticated": False}


@router.get("/me")
async def me(username: Annotated[str, Depends(require_user)]) -> dict:
    return {"authenticated": True, "username": username}
