"""PDF image path helpers."""

from pathlib import Path


def resolve_image_path(raw_path, html_path):
    if not raw_path:
        return None
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = (Path(html_path).parent / path).resolve()
    if path.exists() and path.is_file():
        return path
    return None
