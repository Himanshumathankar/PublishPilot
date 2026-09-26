import html

from app.schemas.article import ArticleDocument


def render_article(article: ArticleDocument, image_urls: dict[str, str]) -> str:
    output: list[str] = []
    for block in article.blocks:
        if block.type == "paragraph":
            output.append(f"<!-- wp:paragraph --><p>{block.html}</p><!-- /wp:paragraph -->")
        elif block.type == "heading":
            output.append(
                f'<!-- wp:heading {{"level":{block.level}}} -->'
                f"<h{block.level}>{html.escape(block.text)}</h{block.level}>"
                "<!-- /wp:heading -->"
            )
        elif block.type == "list":
            tag = "ol" if block.ordered else "ul"
            items = "".join(f"<li>{item.html}</li>" for item in block.items)
            output.append(f"<!-- wp:list --><{tag}>{items}</{tag}><!-- /wp:list -->")
        elif block.type == "table":
            rows = "".join(
                "<tr>" + "".join(f"<td>{cell.html}</td>" for cell in row) + "</tr>"
                for row in block.rows
            )
            output.append(
                '<!-- wp:table --><figure class="wp-block-table">'
                f"<table><tbody>{rows}</tbody></table></figure><!-- /wp:table -->"
            )
        elif block.type == "image":
            url = image_urls[block.image_id]
            caption = (
                '<figcaption class="wp-element-caption" style="text-align:center;">'
                f"{html.escape(block.caption)}</figcaption>"
                if block.caption
                else ""
            )
            output.append(
                '<!-- wp:image {"align":"center"} -->'
                '<figure class="wp-block-image aligncenter">'
                f'<img src="{html.escape(url, quote=True)}" alt=""/>{caption}'
                "</figure><!-- /wp:image -->"
            )
    return "\n".join(output)
