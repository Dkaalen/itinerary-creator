"""Image-bank path handling and scanning."""

from __future__ import annotations

from pathlib import Path

from .metadata import IMAGE_EXTENSIONS, ImageCandidate, extract_image_metadata


def coerce_image_bank_paths(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[Path]:
    if isinstance(image_bank_path, (list, tuple, set)):
        values = list(image_bank_path)
    else:
        values = [image_bank_path]

    paths: list[Path] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        path = Path(value).expanduser()
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def scan_image_bank(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[ImageCandidate]:
    candidates = []
    seen_files: set[str] = set()
    for base in coerce_image_bank_paths(image_bank_path):
        if not base.exists() or not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            key = str(path.resolve())
            if key in seen_files:
                continue
            seen_files.add(key)
            candidates.append(extract_image_metadata(path, base))
    return candidates


# Backwards-compatible private alias for callers/tests that may have imported it.
_coerce_image_bank_paths = coerce_image_bank_paths
