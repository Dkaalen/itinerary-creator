"""Image-bank path handling and scanning."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

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


def _scan_cache_key(image_bank_path: Path | str | list | tuple | set = "image_bank") -> tuple[tuple[str, float, int], ...]:
    key = []
    for base in coerce_image_bank_paths(image_bank_path):
        try:
            resolved = base.resolve()
            if not base.exists():
                key.append((str(resolved), 0.0, 0))
                continue
            newest_mtime = base.stat().st_mtime
            file_count = 0
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                file_count += 1
                try:
                    newest_mtime = max(newest_mtime, path.stat().st_mtime)
                except Exception:
                    pass
            key.append((str(resolved), newest_mtime, file_count))
        except Exception:
            key.append((str(base), 0.0, 0))
    return tuple(key)


@lru_cache(maxsize=16)
def _scan_image_bank_cached(cache_key: tuple[tuple[str, float, int], ...]) -> tuple[ImageCandidate, ...]:
    candidates = []
    seen_files: set[str] = set()
    for path_text, _mtime, _file_count in cache_key:
        base = Path(path_text)
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
    return tuple(candidates)


def scan_image_bank(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[ImageCandidate]:
    return list(_scan_image_bank_cached(_scan_cache_key(image_bank_path)))


# Backwards-compatible private alias for callers/tests that may have imported it.
_coerce_image_bank_paths = coerce_image_bank_paths
