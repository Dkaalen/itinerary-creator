"""Image-bank path handling and scanning."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import hashlib

import diagnostics

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


def _stat_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError as error:
        diagnostics.warn_exception(
            "image_bank_scan",
            "Could not read image-bank file metadata.",
            error,
            str(path),
            source="images.scanner",
        )
        return None
    return int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))), int(stat.st_size)


def _scan_cache_key(image_bank_path: Path | str | list | tuple | set = "image_bank") -> tuple[tuple[str, int, int, int, str], ...]:
    """Return a recursive cache key for image-bank scans.

    Earlier cache keys used only the base directory mtime and file count. That
    can miss nested image replacements on file systems that do not update parent
    directory metadata.  The key now includes nested file mtimes, total size and
    a stable fingerprint of relative paths/sizes/mtimes.
    """

    key = []
    for base in coerce_image_bank_paths(image_bank_path):
        try:
            resolved = base.resolve()
        except OSError as error:
            diagnostics.warn_exception(
                "image_bank_scan",
                "Could not resolve image-bank path.",
                error,
                str(base),
                source="images.scanner",
            )
            resolved = base

        if not base.exists():
            key.append((str(resolved), 0, 0, 0, ""))
            continue

        base_signature = _stat_signature(base) or (0, 0)
        newest_mtime_ns = base_signature[0]
        file_count = 0
        total_size = 0
        fingerprint = hashlib.sha1()

        try:
            paths = sorted(base.rglob("*"))
        except OSError as error:
            diagnostics.warn_exception(
                "image_bank_scan",
                "Could not walk image-bank folder.",
                error,
                str(base),
                source="images.scanner",
            )
            key.append((str(resolved), newest_mtime_ns, 0, 0, "walk-error"))
            continue

        for path in paths:
            try:
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
            except OSError as error:
                diagnostics.warn_exception(
                    "image_bank_scan",
                    "Could not inspect image-bank path.",
                    error,
                    str(path),
                    source="images.scanner",
                )
                continue
            signature = _stat_signature(path)
            if signature is None:
                continue
            mtime_ns, size = signature
            file_count += 1
            total_size += size
            newest_mtime_ns = max(newest_mtime_ns, mtime_ns)
            try:
                relative = path.relative_to(base)
            except ValueError:
                relative = path
            fingerprint.update(str(relative).replace("\\", "/").encode("utf-8", "surrogateescape"))
            fingerprint.update(f":{mtime_ns}:{size};".encode("ascii"))

        key.append((str(resolved), newest_mtime_ns, file_count, total_size, fingerprint.hexdigest()))
    return tuple(key)


@lru_cache(maxsize=16)
def _scan_image_bank_cached(cache_key: tuple[tuple[str, int, int, int, str], ...]) -> tuple[ImageCandidate, ...]:
    candidates = []
    seen_files: set[str] = set()
    for path_text, _mtime, _file_count, _total_size, _fingerprint in cache_key:
        base = Path(path_text)
        if not base.exists() or not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                key = str(path.resolve())
            except OSError as error:
                diagnostics.warn_exception(
                    "image_bank_scan",
                    "Could not resolve image-bank file path.",
                    error,
                    str(path),
                    source="images.scanner",
                )
                continue
            if key in seen_files:
                continue
            seen_files.add(key)
            try:
                candidates.append(extract_image_metadata(path, base))
            except (OSError, ValueError, UnicodeError) as error:
                diagnostics.warn_exception(
                    "image_bank_scan",
                    "Could not read image-bank metadata.",
                    error,
                    str(path),
                    source="images.scanner",
                )
    return tuple(candidates)


def scan_image_bank(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[ImageCandidate]:
    return list(_scan_image_bank_cached(_scan_cache_key(image_bank_path)))


# Backwards-compatible private alias for callers/tests that may have imported it.
_coerce_image_bank_paths = coerce_image_bank_paths
