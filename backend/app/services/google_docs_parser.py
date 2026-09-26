import html
import re
from dataclasses import dataclass

import bleach

from app.schemas.article import ArticleDocument
from app.services.filenames import slugify_filename, unique_filename

ALLOWED_TAGS = ["strong", "em", "a", "br"]
ALLOWED_ATTRS = {"a": ["href"]}


@dataclass
class GoogleImageReference:
    key: str
    content_uri: str
    original_filename: str


@dataclass
class ParsedGoogleDoc:
    article: ArticleDocument
    image_references: list[GoogleImageReference]


def _text_elements(elements: list[dict]) -> str:
    output: list[str] = []
    for element in elements:
        run = element.get("textRun")
        if not run:
            continue
        value = html.escape(run.get("content", "").rstrip("\n"))
        style = run.get("textStyle", {})
        if style.get("link", {}).get("url"):
            value = f'<a href="{html.escape(style["link"]["url"], quote=True)}">{value}</a>'
        if style.get("italic"):
            value = f"<em>{value}</em>"
        if style.get("bold"):
            value = f"<strong>{value}</strong>"
        output.append(value)
    return bleach.clean("".join(output), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _plain_text(elements: list[dict]) -> str:
    return "".join(item.get("textRun", {}).get("content", "") for item in elements).strip()


def _ordered_list(document: dict, list_id: str) -> bool:
    levels = (
        document.get("lists", {})
        .get(list_id, {})
        .get("listProperties", {})
        .get("nestingLevels", [])
    )
    return any(level.get("glyphType") for level in levels)


def _table_rows(table: dict) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for row in table.get("tableRows", []):
        cells: list[dict] = []
        for cell in row.get("tableCells", []):
            parts = [
                _text_elements(content["paragraph"].get("elements", []))
                for content in cell.get("content", [])
                if "paragraph" in content
            ]
            cells.append({"html": "<br>".join(part for part in parts if part)})
        rows.append(cells)
    return rows


def parse_google_document(document: dict) -> ParsedGoogleDoc:
    metadata: dict[str, str] = {}
    title = ""
    blocks: list[dict] = []
    references: list[GoogleImageReference] = []
    used_names: set[str] = set()
    inline_objects = document.get("inlineObjects", {})

    for structural in document.get("body", {}).get("content", []):
        if "table" in structural:
            blocks.append({"type": "table", "rows": _table_rows(structural["table"])})
            continue
        paragraph = structural.get("paragraph")
        if not paragraph:
            continue
        elements = paragraph.get("elements", [])
        text = _plain_text(elements)
        for element in elements:
            object_id = element.get("inlineObjectElement", {}).get("inlineObjectId")
            if not object_id:
                continue
            embedded = (
                inline_objects.get(object_id, {})
                .get("inlineObjectProperties", {})
                .get("embeddedObject", {})
            )
            uri = embedded.get("imageProperties", {}).get("contentUri")
            if uri:
                key = f"image-{len(references) + 1}"
                references.append(GoogleImageReference(key, uri, f"{object_id}.png"))
                blocks.append({"type": "image", "image_id": key, "source": key})

        caption_match = re.match(r"^Figure\s+(\d+)\s*:", text, re.I)
        if caption_match and blocks and blocks[-1]["type"] == "image":
            reference = references[-1]
            filename = unique_filename(slugify_filename(text, ".png", reference.key), used_names)
            reference.original_filename = filename
            blocks[-1].update(
                caption=text,
                figure_number=int(caption_match.group(1)),
                filename=filename,
            )
            continue

        matched_metadata = False
        fields = (
            ("meta_title", "Meta Title:"),
            ("meta_description", "Meta Description:"),
            ("excerpt", "Excerpt:"),
            ("slug", "URL Slug:"),
        )
        for key, label in fields:
            if text.lower().startswith(label.lower()):
                metadata[key] = text[len(label) :].strip()
                matched_metadata = True
                break
        if matched_metadata or not text:
            continue

        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        if style in ("TITLE", "HEADING_1") and not title:
            title = text
        elif style == "HEADING_2":
            blocks.append({"type": "heading", "level": 2, "text": text})
        elif style == "HEADING_3":
            blocks.append({"type": "heading", "level": 3, "text": text})
        elif paragraph.get("bullet"):
            ordered = _ordered_list(document, paragraph["bullet"]["listId"])
            value = _text_elements(elements)
            if blocks and blocks[-1]["type"] == "list" and blocks[-1]["ordered"] == ordered:
                blocks[-1]["items"].append({"html": value})
            else:
                blocks.append({"type": "list", "ordered": ordered, "items": [{"html": value}]})
        elif not any(element.get("inlineObjectElement") for element in elements):
            blocks.append({"type": "paragraph", "html": _text_elements(elements)})

    if not title:
        title = document.get("title", "").strip()
    return ParsedGoogleDoc(ArticleDocument(title=title, blocks=blocks, **metadata), references)
