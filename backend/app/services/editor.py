import html
import re

import bleach

ALLOWED_TAGS = [
    "p",
    "div",
    "span",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "u",
    "s",
    "sub",
    "sup",
    "font",
    "a",
    "br",
    "hr",
    "ul",
    "ol",
    "li",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "figure",
    "img",
    "figcaption",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "div": ["class", "style"],
    "span": ["class", "style"],
    "p": ["class", "style"],
    "h1": ["class", "style"],
    "h2": ["class", "style"],
    "h3": ["class", "style"],
    "h4": ["class", "style"],
    "h5": ["class", "style"],
    "h6": ["class", "style"],
    "font": ["face", "size", "color"],
    "figure": ["class", "style"],
    "img": ["src", "alt", "data-image-id", "class", "style"],
    "figcaption": ["class", "style"],
}


def sanitize_editor_html(value: str) -> str:
    from bleach.css_sanitizer import CSSSanitizer

    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https"],
        css_sanitizer=CSSSanitizer(
            allowed_css_properties=[
                "text-align",
                "color",
                "background-color",
                "font-size",
                "font-family",
                "display",
                "margin-left",
                "margin-right",
            ]
        ),
        strip=True,
    )


def render_editor_html(value: str, image_urls: dict[str, str]) -> str:
    rendered = sanitize_editor_html(value)

    def replace_image(match: re.Match[str]) -> str:
        tag = match.group(0)
        marker = re.search(r'data-image-id=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        if not marker or marker.group(1) not in image_urls:
            return tag
        source = html.escape(image_urls[marker.group(1)], quote=True)
        return re.sub(r'src=["\'][^"\']*["\']', f'src="{source}"', tag, flags=re.IGNORECASE)

    rendered = re.sub(r"<img\b[^>]*>", replace_image, rendered, flags=re.IGNORECASE)

    def append_style(tag: str, declarations: str) -> str:
        style = re.search(r'\sstyle=["\']([^"\']*)["\']', tag, re.IGNORECASE)
        if style:
            existing = style.group(1).strip().rstrip(";")
            merged = f"{existing};{declarations}" if existing else declarations
            return tag[: style.start(1)] + merged + tag[style.end(1) :]
        return tag[:-1] + f' style="{declarations}">'

    def enforce_image_alignment(match: re.Match[str]) -> str:
        opening, body, closing = match.groups()
        class_attribute = re.search(
            r'class=["\']([^"\']*)["\']', opening, re.IGNORECASE
        )
        classes = class_attribute.group(1).split() if class_attribute else []
        if "aligncenter" not in classes:
            return match.group(0)
        opening = append_style(opening, "text-align:center;")
        body = re.sub(
            r"<img\b[^>]*>",
            lambda image: append_style(
                image.group(0),
                "display:block;margin-left:auto;margin-right:auto;",
            ),
            body,
            count=1,
            flags=re.IGNORECASE,
        )
        return opening + body + closing

    return re.sub(
        r"(<figure\b[^>]*>)(.*?)(</figure>)",
        enforce_image_alignment,
        rendered,
        flags=re.IGNORECASE | re.DOTALL,
    )
