import uuid
from pathlib import Path

from app.core.config import get_settings


class ArticleStorage:
    def __init__(self) -> None:
        self.root = Path(get_settings().article_storage_path).resolve()

    def save(self, article_id: uuid.UUID, image_id: uuid.UUID, filename: str, data: bytes) -> str:
        directory = self.root / str(article_id)
        directory.mkdir(parents=True, exist_ok=True)
        destination = (directory / f"{image_id}-{Path(filename).name}").resolve()
        if self.root not in destination.parents:
            raise ValueError("Unsafe storage path")
        destination.write_bytes(data)
        return str(destination)

    def read(self, path: str) -> bytes:
        resolved = Path(path).resolve()
        if self.root not in resolved.parents:
            raise ValueError("Unsafe storage path")
        return resolved.read_bytes()
