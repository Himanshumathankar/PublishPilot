import io

from PIL import Image

from app.services.images import convert_to_webp


def test_image_conversion_produces_lossless_webp() -> None:
    source = io.BytesIO()
    Image.new("RGBA", (12, 9), (200, 10, 20, 128)).save(source, format="PNG")

    data, filename, mime = convert_to_webp(source.getvalue(), "source.png")

    assert filename == "source.webp"
    assert mime == "image/webp"
    with Image.open(io.BytesIO(data)) as converted:
        assert converted.format == "WEBP"
        assert converted.size == (12, 9)
        assert converted.mode == "RGBA"


def test_large_image_is_optimized_below_wordpress_limit() -> None:
    source = io.BytesIO()
    Image.effect_noise((1600, 1200), 100).convert("RGB").save(source, format="PNG")

    data, filename, mime = convert_to_webp(
        source.getvalue(), "large-photo.png", max_bytes=300_000
    )

    assert len(data) <= 300_000
    assert filename == "large-photo.webp"
    assert mime == "image/webp"
