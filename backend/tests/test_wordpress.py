from unittest.mock import AsyncMock

import pytest

from app.services.errors import ServiceError
from app.services.wordpress import WordPressService


def wordpress_with_response(response: dict) -> WordPressService:
    service = object.__new__(WordPressService)
    service.request = AsyncMock(return_value=response)
    return service


@pytest.mark.asyncio
async def test_post_verification_accepts_expected_publishing_fields() -> None:
    service = wordpress_with_response(
        {
            "slug": "exact-slug",
            "status": "draft",
            "featured_media": 45,
            "categories": [8],
            "author": 4,
        }
    )

    await service.verify_post(
        123,
        {
            "slug": "exact-slug",
            "status": "draft",
            "featured_media": 45,
            "categories": [8],
            "author": 4,
        },
    )

    service.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_verification_reports_mismatched_fields() -> None:
    service = wordpress_with_response(
        {
            "slug": "changed",
            "status": "draft",
            "featured_media": 45,
            "categories": [8],
            "author": 4,
        }
    )

    with pytest.raises(ServiceError) as raised:
        await service.verify_post(
            123,
            {
                "slug": "exact-slug",
                "status": "draft",
                "featured_media": 45,
                "categories": [8],
                "author": 4,
            },
        )

    assert raised.value.code == "WORDPRESS_POST_VERIFY_ERROR"
