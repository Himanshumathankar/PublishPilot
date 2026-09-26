import pytest

from app.services.errors import ServiceError
from app.services.google_sheets import spreadsheet_id_from_url
from app.services.google_sheets_parser import parse_field_value_sheet, sheet_overrides


def test_field_value_sheet_supports_any_row_order_and_structured_content() -> None:
    parsed = parse_field_value_sheet(
        [
            ["Field", "Value"],
            ["URL Slug", "exact-slug"],
            ["Paragraph", "First <strong>paragraph</strong>"],
            ["Article Title", "Exact title"],
            ["Heading 2", "Exact section"],
            ["Bullet Item", "One"],
            ["Bullet Item", "Two"],
            ["Meta Description", "Exact description"],
            ["Meta Title", "Exact meta"],
        ]
    )

    assert parsed.article is not None
    assert parsed.article.title == "Exact title"
    assert parsed.article.meta_title == "Exact meta"
    assert [block.type for block in parsed.article.blocks] == ["paragraph", "heading", "list"]
    assert len(parsed.article.blocks[2].items) == 2


def test_sheet_can_delegate_body_to_google_doc_and_override_metadata() -> None:
    rows = [
        ["Article URL", "https://docs.google.com/document/d/abc/edit"],
        ["Meta Title", "Sheet-owned meta"],
        ["Article Title", "Sheet-owned title"],
    ]
    parsed = parse_field_value_sheet(rows)
    assert parsed.article is None
    assert parsed.article_url == "https://docs.google.com/document/d/abc/edit"
    assert sheet_overrides(rows) == {
        "title": "Sheet-owned title",
        "meta_title": "Sheet-owned meta",
    }


def test_google_sheet_url_validation() -> None:
    url = "https://docs.google.com/spreadsheets/d/sheet_123-ABC/edit#gid=0"
    assert spreadsheet_id_from_url(url) == "sheet_123-ABC"
    with pytest.raises(ServiceError) as error:
        spreadsheet_id_from_url("https://example.com/not-a-sheet")
    assert error.value.code == "INVALID_GOOGLE_SHEET_URL"
