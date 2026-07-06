"""App-scoped image-bank accessors.

Core image-bank modules accept an explicit root/path. Streamlit-facing code uses
this module so the app root and storage signature logic have one owner instead
of being mixed into day-image selection helpers.
"""

from __future__ import annotations

from pathlib import Path

from images.image_bank import (
    APP_ROOT,
    connect_remote_image_bank_if_missing as _connect_remote_image_bank_if_missing,
    ensure_runtime_image_bank as _ensure_runtime_image_bank,
    ensure_runtime_image_bank_status as _ensure_runtime_image_bank_status,
    get_image_bank_path as _get_image_bank_path,
    get_image_bank_paths as _get_image_bank_paths,
    get_image_bank_scan_paths as _get_image_bank_scan_paths,
    image_bank_status as _image_bank_status,
    infer_country_for_city as _infer_country_for_city,
    prefetch_image_bank_for_rows as _prefetch_image_bank_for_rows,
)

IMAGE_STORAGE_SUFFIXES = frozenset({".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"})


def _app_root(root: Path | str | None = None) -> Path:
    return Path(root) if root is not None else APP_ROOT


def ensure_runtime_image_bank(required_destinations=None, *, root: Path | str | None = None):
    return _ensure_runtime_image_bank(_app_root(root), required_destinations=required_destinations)


def ensure_runtime_image_bank_status(required_destinations=None, *, root: Path | str | None = None):
    return _ensure_runtime_image_bank_status(_app_root(root), required_destinations=required_destinations)


def connect_remote_image_bank_if_missing(required_destinations=None, *, root: Path | str | None = None):
    return _connect_remote_image_bank_if_missing(_app_root(root), required_destinations=required_destinations)


def image_bank_status(required_destinations=None, *, root: Path | str | None = None):
    return _image_bank_status(_app_root(root), required_destinations=required_destinations)


def prefetch_image_bank_for_rows(rows_or_grouped_days, *, root: Path | str | None = None):
    return _prefetch_image_bank_for_rows(rows_or_grouped_days, _app_root(root))


def get_image_bank_paths(*, root: Path | str | None = None):
    return _get_image_bank_paths(_app_root(root))


def get_image_bank_path(*, root: Path | str | None = None):
    return _get_image_bank_path(_app_root(root))


def get_image_bank_scan_paths(*, root: Path | str | None = None):
    return _get_image_bank_scan_paths(_app_root(root))


def infer_country_for_city(city, *, root: Path | str | None = None):
    return _infer_country_for_city(city, _app_root(root))


def image_bank_storage_signature(*, root: Path | str | None = None):
    """Return a lightweight signature for the active image-bank storage."""

    parts = []
    for path in get_image_bank_scan_paths(root=root):
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if not path.exists() or not path.is_dir():
            parts.append((str(resolved), "missing", 0, 0, 0))
            continue
        count = 0
        total_size = 0
        newest_mtime = 0
        for candidate in path.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_STORAGE_SUFFIXES:
                continue
            try:
                stat = candidate.stat()
            except OSError:
                continue
            count += 1
            total_size += int(stat.st_size)
            newest_mtime = max(newest_mtime, int(stat.st_mtime_ns))
        parts.append((str(resolved), "present", count, total_size, newest_mtime))
    return repr(parts)
