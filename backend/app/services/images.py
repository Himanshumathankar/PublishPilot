import io
import math
from pathlib import Path

from PIL import Image, ImageOps

from app.services.errors import ServiceError


def convert_to_webp(
    data: bytes, filename: str, max_bytes: int | None = None
) -> tuple[bytes, str, str]:
    """Convert to WebP, preserving losslessly when it fits the upload ceiling."""
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format == "WEBP" and (not max_bytes or len(data) <= max_bytes):
                return data, f"{Path(filename).stem}.webp", "image/webp"
            image = ImageOps.exif_transpose(source)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            output = io.BytesIO()
            image.save(output, format="WEBP", lossless=True, method=6)
            if max_bytes and output.tell() > max_bytes:
                for quality in (90, 85, 80, 75, 70, 65, 60):
                    output = io.BytesIO()
                    image.save(output, format="WEBP", quality=quality, method=6)
                    if output.tell() <= max_bytes:
                        break
            while max_bytes and output.tell() > max_bytes and min(image.size) > 640:
                ratio = min(0.9, math.sqrt(max_bytes / output.tell()) * 0.95)
                dimensions = (
                    max(1, round(image.width * ratio)),
                    max(1, round(image.height * ratio)),
                )
                image = image.resize(dimensions, Image.Resampling.LANCZOS)
                output = io.BytesIO()
                image.save(output, format="WEBP", quality=80, method=6)
            if max_bytes and output.tell() > max_bytes:
                raise ValueError("image cannot fit the configured upload limit")
    except Exception as exc:
        raise ServiceError(
            "IMAGE_CONVERSION_ERROR", f"Could not convert {filename} to WebP."
        ) from exc
    return output.getvalue(), f"{Path(filename).stem}.webp", "image/webp"
