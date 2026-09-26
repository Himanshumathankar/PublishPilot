import pytest

from app.services.errors import ServiceError
from app.services.google_docs import document_id_from_url
from app.services.google_docs_parser import parse_google_document


def paragraph(text: str, style: str = "NORMAL_TEXT", **extra) -> dict:
    return {
        "paragraph": {
            "paragraphStyle": {"namedStyleType": style},
            "elements": [{"textRun": {"content": f"{text}\n", "textStyle": extra}}],
        }
    }


def test_google_document_maps_to_common_representation() -> None:
    document = {
        "title": "Drive filename",
        "body": {
            "content": [
                paragraph("Meta Title: Exact meta"),
                paragraph("Meta Description: Exact description"),
                paragraph("URL Slug: exact-slug"),
                paragraph("Exact title", "HEADING_1"),
                paragraph("Linked text", link={"url": "https://example.test"}, bold=True),
                paragraph("Section", "HEADING_2"),
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [{"inlineObjectElement": {"inlineObjectId": "object-1"}}],
                    }
                },
                paragraph("Figure 1: Exact image caption. Image credit: Source."),
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {"content": [paragraph("A")]},
                                    {"content": [paragraph("B")]},
                                ]
                            }
                        ]
                    }
                },
            ]
        },
        "inlineObjects": {
            "object-1": {
                "inlineObjectProperties": {
                    "embeddedObject": {"imageProperties": {"contentUri": "https://image.test/1"}}
                }
            }
        },
    }

    parsed = parse_google_document(document)
    assert parsed.article.title == "Exact title"
    assert parsed.article.meta_title == "Exact meta"
    assert parsed.article.slug == "exact-slug"
    assert [block.type for block in parsed.article.blocks] == [
        "paragraph",
        "heading",
        "image",
        "table",
    ]
    assert (
        parsed.article.blocks[0].html
        == '<strong><a href="https://example.test">Linked text</a></strong>'
    )
    assert parsed.article.blocks[2].filename == "exact-image-caption.png"
    assert parsed.image_references[0].content_uri == "https://image.test/1"


def test_google_doc_url_validation() -> None:
    assert (
        document_id_from_url("https://docs.google.com/document/d/abc_123-XYZ/edit") == "abc_123-XYZ"
    )
    with pytest.raises(ServiceError) as error:
        document_id_from_url("https://example.com/not-a-doc")
    assert error.value.code == "INVALID_GOOGLE_DOC_URL"
