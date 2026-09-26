import re
import unicodedata
from pathlib import Path


def slugify_filename(value: str, extension: str, fallback: str, max_stem: int = 120) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = re.sub(r"^\s*figure\s+\d+\s*:\s*", "", normalized, flags=re.I)
    normalized = re.sub(r"\bimage\s+credit\s*:.*$", "", normalized, flags=re.I)
    normalized = normalized.replace("'", "")
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()[:max_stem].rstrip("-")
    ext = re.sub(r"[^a-zA-Z0-9]", "", Path(extension).suffix or extension).lower()
    return f"{stem or fallback}.{ext or 'jpg'}"


def slugify_slug(value: str, fallback: str = "article", max_length: int = 200) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = normalized.replace("'", "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug[:max_length].rstrip("-") or fallback


def unique_filename(filename: str, used: set[str]) -> str:
    path = Path(filename)
    candidate = filename
    counter = 2
    while candidate in used:
        candidate = f"{path.stem}-{counter}{path.suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def media_title(caption: str) -> str:
    value = re.sub(r"^\s*figure\s+\d+\s*:\s*", "", caption, flags=re.I)
    return re.sub(r"\s*image\s+credit\s*:.*$", "", value, flags=re.I).strip().rstrip(".")
