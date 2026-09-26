import asyncio
import io
import re

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from googleapiclient.discovery import build
from PIL import Image

from app.core.config import get_settings
from app.services.docx_parser import ExtractedImage
from app.services.errors import ServiceError
from app.services.google_docs_parser import ParsedGoogleDoc, parse_google_document

DOC_ID_PATTERN = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")
SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def document_id_from_url(url: str) -> str:
    match = DOC_ID_PATTERN.search(url)
    if not match:
        raise ServiceError("INVALID_GOOGLE_DOC_URL", "Enter a valid Google Docs URL.")
    return match.group(1)


class GoogleDocsService:
    def __init__(self, credentials_path: str | None = None) -> None:
        self.credentials_path = credentials_path

    def _credentials(self):
        path = self.credentials_path or get_settings().google_application_credentials
        try:
            if path:
                return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
            credentials, _ = google.auth.default(scopes=SCOPES)
            return credentials
        except Exception as exc:
            raise ServiceError(
                "GOOGLE_AUTH_ERROR", "Google API credentials are not configured.", 503
            ) from exc

    def _fetch(self, document_id: str) -> tuple[dict, object]:
        credentials = self._credentials()
        try:
            service = build("docs", "v1", credentials=credentials, cache_discovery=False)
            document = service.documents().get(documentId=document_id).execute()
            return document, credentials
        except Exception as exc:
            raise ServiceError(
                "GOOGLE_DOC_NOT_ACCESSIBLE",
                "The Google Doc is not accessible to the configured account.",
                502,
            ) from exc

    def _download_images(
        self, parsed: ParsedGoogleDoc, credentials: object
    ) -> list[ExtractedImage]:
        session = AuthorizedSession(credentials)
        images: list[ExtractedImage] = []
        for reference in parsed.image_references:
            response = session.get(reference.content_uri, timeout=30)
            if not response.ok:
                raise ServiceError(
                    "IMAGE_EXTRACTION_ERROR",
                    f"Could not download {reference.key} from Google Docs.",
                    502,
                )
            data = response.content
            try:
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                    image_format = image.format or "PNG"
                    mime = Image.MIME.get(
                        image_format, response.headers.get("content-type", "image/png")
                    )
            except Exception as exc:
                raise ServiceError(
                    "IMAGE_EXTRACTION_ERROR", f"Google Docs image {reference.key} is invalid."
                ) from exc
            block = next(
                item
                for item in parsed.article.blocks
                if getattr(item, "image_id", None) == reference.key
            )
            filename = block.filename or f"{reference.key}.{image_format.lower()}"
            images.append(
                ExtractedImage(
                    reference.key,
                    reference.original_filename,
                    filename,
                    mime,
                    data,
                    block.caption,
                    block.figure_number,
                )
            )
        return images

    async def import_document(self, url: str):
        document, credentials = await asyncio.to_thread(self._fetch, document_id_from_url(url))
        parsed = parse_google_document(document)
        images = await asyncio.to_thread(self._download_images, parsed, credentials)
        return parsed.article, images
