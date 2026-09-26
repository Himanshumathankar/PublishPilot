from dataclasses import dataclass

import bleach

from app.schemas.article import ArticleDocument
from app.services.errors import ServiceError


def _key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _safe(value: str) -> str:
    return bleach.clean(
        value, tags=["strong", "em", "a", "br"], attributes={"a": ["href"]}, strip=True
    )


@dataclass
class ParsedSheet:
    article: ArticleDocument | None
    article_url: str | None


def parse_field_value_sheet(rows: list[list[str]]) -> ParsedSheet:
    values: dict[str, str] = {}
    blocks: list[dict] = []
    current_list: dict | None = None

    for row in rows:
        if not row or not str(row[0]).strip():
            continue
        field = _key(str(row[0]))
        value = str(row[1]) if len(row) > 1 else ""
        if field in {"field", "key", "name"} and _key(value) == "value":
            continue
        values[field] = value
        if field in {"paragraph", "body paragraph", "also read"}:
            blocks.append({"type": "paragraph", "html": _safe(value)})
            current_list = None
        elif field in {"heading 2", "h2"}:
            blocks.append({"type": "heading", "level": 2, "text": value})
            current_list = None
        elif field in {"heading 3", "h3", "disclaimer heading"}:
            blocks.append({"type": "heading", "level": 3, "text": value})
            current_list = None
        elif field in {"bullet", "bullet item", "numbered item", "number item"}:
            ordered = field in {"numbered item", "number item"}
            if current_list is None or current_list["ordered"] != ordered:
                current_list = {"type": "list", "ordered": ordered, "items": []}
                blocks.append(current_list)
            current_list["items"].append({"html": _safe(value)})
        else:
            current_list = None

    article_url = values.get("article url") or values.get("google doc url")
    title = values.get("article title") or values.get("title")
    content = values.get("article content") or values.get("content")
    if content and not blocks:
        blocks = [
            {"type": "paragraph", "html": _safe(paragraph.replace("\n", "<br>"))}
            for paragraph in content.split("\n\n")
            if paragraph
        ]
    if article_url:
        return ParsedSheet(None, article_url)
    if not title:
        raise ServiceError(
            "GOOGLE_SHEET_FORMAT_ERROR",
            "The sheet must contain Article Title or an Article URL.",
        )
    return ParsedSheet(
        ArticleDocument(
            title=title,
            meta_title=values.get("meta title"),
            meta_description=values.get("meta description"),
            excerpt=values.get("excerpt"),
            slug=values.get("url slug") or values.get("slug"),
            blocks=blocks,
        ),
        None,
    )


def sheet_overrides(rows: list[list[str]]) -> dict[str, str]:
    mapped = {
        _key(str(row[0])): str(row[1]) for row in rows if len(row) > 1 and str(row[0]).strip()
    }
    result: dict[str, str] = {}
    for target, options in {
        "title": ("article title", "title"),
        "meta_title": ("meta title",),
        "meta_description": ("meta description",),
        "excerpt": ("excerpt",),
        "slug": ("url slug", "slug"),
    }.items():
        value = next((mapped[key] for key in options if mapped.get(key)), None)
        if value:
            result[target] = value
    return result
