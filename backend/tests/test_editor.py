from app.services.editor import render_editor_html, sanitize_editor_html


def test_editor_sanitizes_scripts_and_event_handlers() -> None:
    value = '<p onclick="alert(1)">Safe <strong>text</strong></p><script>bad()</script>'

    sanitized = sanitize_editor_html(value)

    assert "onclick" not in sanitized
    assert "<script" not in sanitized
    assert "<strong>text</strong>" in sanitized


def test_editor_replaces_local_image_source_for_wordpress() -> None:
    value = '<figure><img data-image-id="image-1" src="http://localhost/image"></figure>'

    rendered = render_editor_html(value, {"image-1": "https://example.test/media.webp"})

    assert 'src="https://example.test/media.webp"' in rendered
    assert "localhost" not in rendered


def test_editor_preserves_also_read_highlight_class() -> None:
    sanitized = sanitize_editor_html(
        '<p class="highlight-also-read">Also Read: Related story</p>'
    )

    assert 'class="highlight-also-read"' in sanitized
