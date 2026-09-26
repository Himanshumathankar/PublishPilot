import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import IntegrationSettings
from app.services.errors import ServiceError


def _cipher() -> Fernet:
    digest = hashlib.sha256(get_settings().app_secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ServiceError(
            "INTEGRATION_CREDENTIAL_ERROR",
            "Stored credentials cannot be decrypted. Re-enter them in Settings.",
            503,
        ) from exc


async def integration_settings(db: AsyncSession) -> IntegrationSettings:
    record = await db.get(IntegrationSettings, 1)
    if not record:
        record = IntegrationSettings(id=1)
        db.add(record)
        await db.flush()
    return record
