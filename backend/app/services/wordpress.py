import base64
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.errors import ServiceError


class WordPressService:
    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        application_password: str | None = None,
        rank_math_endpoint: str | None = None,
    ) -> None:
        settings = get_settings()
        base_url = base_url or settings.wordpress_base_url
        username = username or settings.wordpress_username
        application_password = application_password or settings.wordpress_application_password
        if not all(
            (
                base_url,
                username,
                application_password,
            )
        ):
            raise ServiceError(
                "WORDPRESS_NOT_CONFIGURED", "WordPress credentials are not configured.", 503
            )
        self.base = base_url.rstrip("/")
        self.rank_math_endpoint = rank_math_endpoint or settings.rank_math_endpoint
        token = base64.b64encode(f"{username}:{application_password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def request(self, method: str, path: str, **kwargs: Any) -> dict | list:
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.request(
                    method, f"{self.base}{path}", headers=self.headers, **kwargs
                )
        except (httpx.TimeoutException, httpx.NetworkError):
            raise
        if response.status_code in (401, 403):
            raise ServiceError("WORDPRESS_AUTH_ERROR", "WordPress authentication failed.", 502)
        if response.is_error:
            detail = ""
            try:
                body = response.json()
                if isinstance(body, dict):
                    wordpress_code = str(body.get("code") or "").strip()
                    wordpress_message = str(body.get("message") or "").strip()
                    if wordpress_code or wordpress_message:
                        detail = f" {wordpress_code}: {wordpress_message}"[:500]
            except ValueError:
                pass
            raise ServiceError(
                "WORDPRESS_API_ERROR",
                f"WordPress returned HTTP {response.status_code}.{detail}",
                502,
            )
        return response.json()

    async def categories(self) -> list[dict]:
        result = await self._all_pages("/wp-json/wp/v2/categories", {"hide_empty": False})
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "parent": item.get("parent", 0),
                "count": item.get("count", 0),
            }
            for item in result
        ]

    async def authors(self) -> list[dict]:
        try:
            try:
                plugin_authors = await self.request("GET", "/wp-json/twpublisher/v1/authors")
            except ServiceError:
                try:
                    plugin_authors = await self.request(
                        "GET", "/wp-json/publishpilot/v1/authors"
                    )
                except ServiceError:
                    plugin_authors = await self.request(
                        "GET", "/wp-json/article-publisher/v1/authors"
                    )
            if not isinstance(plugin_authors, list):
                raise ServiceError("WORDPRESS_API_ERROR", "Invalid author list.", 502)
            result = plugin_authors
        except ServiceError:
            try:
                result = await self._all_pages(
                    "/wp-json/wp/v2/users", {"context": "edit", "who": "authors"}
                )
            except ServiceError:
                # Older plugin versions still allow publishing as the authenticated user.
                current = await self.request(
                    "GET", "/wp-json/wp/v2/users/me", params={"context": "edit"}
                )
                if not isinstance(current, dict) or not current.get("id"):
                    raise ServiceError(
                        "WORDPRESS_AUTHORS_UNAVAILABLE",
                        "WordPress does not allow this account to read authors.",
                        502,
                    ) from None
                result = [current]
        return [
            {
                "id": item["id"],
                "name": item.get("name") or item.get("display_name") or "WordPress user",
                "username": item.get("username")
                or item.get("user_login")
                or item.get("slug")
                or "",
            }
            for item in result
        ]

    async def _all_pages(self, path: str, params: dict) -> list[dict]:
        first = await self.request(
            "GET", path, params={**params, "per_page": 100, "page": 1, "_envelope": 1}
        )
        if not isinstance(first, dict) or not isinstance(first.get("body"), list):
            raise ServiceError("WORDPRESS_API_ERROR", "WordPress returned an invalid list.", 502)
        items = list(first["body"])
        headers = {key.lower(): value for key, value in first.get("headers", {}).items()}
        total_pages = int(headers.get("x-wp-totalpages", 1))
        for page in range(2, total_pages + 1):
            response = await self.request(
                "GET", path, params={**params, "per_page": 100, "page": page}
            )
            if not isinstance(response, list):
                raise ServiceError(
                    "WORDPRESS_API_ERROR", "WordPress returned an invalid list.", 502
                )
            items.extend(response)
        return items

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _post_media(self, headers: dict[str, str], data: bytes) -> httpx.Response:
        async with httpx.AsyncClient(timeout=60) as client:
            return await client.post(
                f"{self.base}/wp-json/wp/v2/media", headers=headers, content=data
            )

    async def upload_media(
        self,
        data: bytes,
        filename: str,
        mime: str,
        title: str,
        caption: str = "",
        alt_text: str = "",
    ) -> dict:
        headers = {
            **self.headers,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime,
        }
        try:
            response = await self._post_media(headers, data)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ServiceError(
                "WORDPRESS_MEDIA_UPLOAD_ERROR", f"Could not upload {filename}.", 502
            ) from exc
        if response.status_code == 413:
            raise ServiceError(
                "WORDPRESS_MEDIA_TOO_LARGE",
                f"WordPress rejected {filename} because it exceeds the server upload limit.",
                502,
            )
        if response.is_error:
            raise ServiceError("WORDPRESS_MEDIA_UPLOAD_ERROR", f"Could not upload {filename}.", 502)
        media = response.json()
        await self.update_media_metadata(media["id"], title, caption, alt_text)
        return media

    async def update_media_metadata(
        self, media_id: int, title: str, caption: str, alt_text: str = ""
    ) -> None:
        await self.request(
            "POST",
            f"/wp-json/wp/v2/media/{media_id}",
            json={"title": title, "caption": caption, "alt_text": alt_text},
        )

    async def create_post(self, payload: dict) -> dict:
        try:
            return await self.request("POST", "/wp-json/wp/v2/posts", json=payload)
        except ServiceError as exc:
            if exc.code == "WORDPRESS_API_ERROR":
                raise ServiceError(
                    "WORDPRESS_POST_CREATE_ERROR",
                    f"WordPress could not create the post. {exc.message}",
                    502,
                ) from exc
            raise

    async def update_post(self, post_id: int, payload: dict) -> dict:
        try:
            return await self.request("POST", f"/wp-json/wp/v2/posts/{post_id}", json=payload)
        except ServiceError as exc:
            if exc.code == "WORDPRESS_API_ERROR":
                raise ServiceError(
                    "WORDPRESS_POST_UPDATE_ERROR",
                    f"WordPress could not update the post. {exc.message}",
                    502,
                ) from exc
            raise

    async def posts_by_slug(self, slug: str) -> list[dict]:
        result = await self.request(
            "GET",
            "/wp-json/wp/v2/posts",
            params={"slug": slug, "context": "edit", "status": "any", "per_page": 100},
        )
        return result if isinstance(result, list) else []

    async def verify_post(self, post_id: int, expected: dict) -> None:
        try:
            post = await self.request(
                "GET", f"/wp-json/wp/v2/posts/{post_id}", params={"context": "edit"}
            )
            if not isinstance(post, dict):
                raise ValueError("unexpected response")
            actual_categories = set(post.get("categories", []))
            expected_categories = set(expected["categories"])
            mismatches = []
            if post.get("slug") != expected["slug"]:
                mismatches.append(f"slug is '{post.get('slug')}' instead of '{expected['slug']}'")
            if post.get("status") != expected["status"]:
                mismatches.append(
                    f"status is '{post.get('status')}' instead of '{expected['status']}'"
                )
            if post.get("featured_media") != expected["featured_media"]:
                mismatches.append("featured image differs")
            if post.get("author") != expected["author"]:
                mismatches.append(f"author is {post.get('author')} instead of {expected['author']}")
            if not expected_categories.issubset(actual_categories):
                actual = sorted(actual_categories)
                wanted = sorted(expected_categories)
                mismatches.append(f"categories are {actual} instead of including {wanted}")
            if mismatches:
                raise ServiceError(
                    "WORDPRESS_POST_VERIFY_ERROR",
                    "WordPress saved the post with different fields: "
                    + "; ".join(mismatches)
                    + ".",
                    502,
                )
        except ServiceError as exc:
            if exc.code == "WORDPRESS_POST_VERIFY_ERROR":
                raise
            raise ServiceError(
                "WORDPRESS_POST_VERIFY_ERROR",
                "The WordPress post was created but its fields could not be verified.",
                502,
            ) from exc
        except (ValueError, TypeError) as exc:
            raise ServiceError(
                "WORDPRESS_POST_VERIFY_ERROR",
                "The WordPress post was created but returned an invalid verification response.",
                502,
            ) from exc

    async def apply_rank_math(self, post_id: int, title: str, description: str) -> None:
        endpoint = self.rank_math_endpoint
        try:
            if endpoint:
                result = await self.request(
                    "POST",
                    endpoint if endpoint.startswith("/") else f"/{endpoint}",
                    json={"post_id": post_id, "title": title, "description": description},
                )
                if not isinstance(result, dict) or result.get("success") is False:
                    raise ServiceError(
                        "RANK_MATH_UPDATE_ERROR", "Rank Math rejected the SEO metadata.", 502
                    )
                return
            result = await self.request(
                "POST",
                f"/wp-json/wp/v2/posts/{post_id}",
                json={"meta": {"rank_math_title": title, "rank_math_description": description}},
            )
            meta = result.get("meta", {}) if isinstance(result, dict) else {}
            if (
                meta.get("rank_math_title") != title
                or meta.get("rank_math_description") != description
            ):
                raise ServiceError(
                    "RANK_MATH_UPDATE_ERROR",
                    "Rank Math fields are not exposed through WordPress REST. "
                    "Configure RANK_MATH_ENDPOINT.",
                    502,
                )
        except ServiceError as exc:
            if exc.code == "RANK_MATH_UPDATE_ERROR":
                raise
            raise ServiceError(
                "RANK_MATH_UPDATE_ERROR", "Rank Math metadata could not be applied.", 502
            ) from exc
