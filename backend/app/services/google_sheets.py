import asyncio
import re

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.core.config import get_settings
from app.services.errors import ServiceError
from app.services.google_docs import GoogleDocsService
from app.services.google_sheets_parser import parse_field_value_sheet, sheet_overrides

SHEET_ID_PATTERN = re.compile(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def spreadsheet_id_from_url(url: str) -> str:
    match = SHEET_ID_PATTERN.search(url)
    if not match:
        raise ServiceError("INVALID_GOOGLE_SHEET_URL", "Enter a valid Google Sheets URL.")
    return match.group(1)


class GoogleSheetsService:
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

    def _fetch_rows(self, spreadsheet_id: str) -> list[list[str]]:
        try:
            service = build("sheets", "v4", credentials=self._credentials(), cache_discovery=False)
            metadata = (
                service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
                .execute()
            )
            sheets = metadata.get("sheets", [])
            if not sheets:
                raise ServiceError("GOOGLE_SHEET_FORMAT_ERROR", "The spreadsheet has no tabs.")
            title = sheets[0]["properties"]["title"].replace("'", "''")
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=f"'{title}'!A:Z")
                .execute()
            )
            return result.get("values", [])
        except ServiceError:
            raise
        except Exception as exc:
            raise ServiceError(
                "GOOGLE_SHEET_NOT_ACCESSIBLE",
                "The Google Sheet is not accessible to the configured account.",
                502,
            ) from exc

    async def import_spreadsheet(self, url: str):
        rows = await asyncio.to_thread(self._fetch_rows, spreadsheet_id_from_url(url))
        parsed = parse_field_value_sheet(rows)
        if parsed.article_url:
            document, images = await GoogleDocsService(self.credentials_path).import_document(
                parsed.article_url
            )
            updates = sheet_overrides(rows)
            document = document.model_copy(update=updates)
            return document, images
        return parsed.article, []
