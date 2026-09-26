import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.article import ArticleDocument


def test_common_article_representation_preserves_block_order() -> None:
    article = ArticleDocument.model_validate(
        {
            "title": "Exact source title",
            "meta_title": "Exact meta title",
            "meta_description": "Exact description",
            "slug": "exact-slug",
            "blocks": [
                {"type": "paragraph", "html": "First"},
                {
                    "type": "image",
                    "image_id": "image-1",
                    "source": "word/media/image1.png",
                    "caption": "Figure 1: Exact caption.",
                },
                {"type": "heading", "level": 2, "text": "Exact heading"},
                {"type": "table", "rows": [[{"html": "A"}, {"html": "B"}]]},
            ],
        }
    )

    assert [block.type for block in article.blocks] == ["paragraph", "image", "heading", "table"]
    assert article.blocks[1].caption == "Figure 1: Exact caption."


def test_h1_is_not_valid_as_body_heading() -> None:
    with pytest.raises(ValidationError):
        ArticleDocument.model_validate(
            {"title": "Title", "blocks": [{"type": "heading", "level": 1, "text": "Duplicate"}]}
        )


def test_cors_origins_accept_comma_separated_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    assert Settings().backend_cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", app_secret_key="development-only-secret-key-change-me")
