from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl


class TextBlock(BaseModel):
    type: Literal["paragraph"]
    html: str


class HeadingBlock(BaseModel):
    type: Literal["heading"]
    level: Literal[2, 3]
    text: str


class ListItem(BaseModel):
    html: str


class ListBlock(BaseModel):
    type: Literal["list"]
    ordered: bool
    items: list[ListItem]


class ImageBlock(BaseModel):
    type: Literal["image"]
    image_id: str
    source: str
    caption: str | None = None
    figure_number: int | None = None
    filename: str | None = None


class TableCell(BaseModel):
    html: str


class TableBlock(BaseModel):
    type: Literal["table"]
    rows: list[list[TableCell]]


ArticleBlock = Annotated[
    TextBlock | HeadingBlock | ListBlock | ImageBlock | TableBlock,
    Field(discriminator="type"),
]


class ArticleDocument(BaseModel):
    title: str
    meta_title: str | None = None
    meta_description: str | None = None
    excerpt: str | None = None
    slug: str | None = None
    blocks: list[ArticleBlock]


class PublishedArticle(BaseModel):
    wordpress_post_id: int
    wordpress_url: HttpUrl
