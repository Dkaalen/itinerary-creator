"""Cached image-bank index API and compatibility facade."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from threading import RLock
import time

from images.image_bank_index import ImageBankIndex, build_image_bank_index
from images.image_bank_paths import coerce_image_bank_paths, fast_paths_signature, path_set_key
from images.image_bank_scan import scan_cache_key as _scan_cache_key
from images.metadata import ImageCandidate


@dataclass(slots=True)
class _CachedIndex:
    index: ImageBankIndex
    validated_at: float
    fast_signature: tuple[tuple[str, int, int], ...]


_INDEX_CACHE: dict[tuple[str, ...], _CachedIndex] = {}
_INDEX_LOCK = RLock()


def _validation_interval_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get("ITINERARY_IMAGE_INDEX_VALIDATE_SECONDS", "30")))
    except (TypeError, ValueError):
        return 30.0


def _recursive_cache_key(path_key: tuple[str, ...]) -> str:
    return _scan_cache_key([Path(path) for path in path_key])


def _cached_index_is_fresh(cached: _CachedIndex, *, now: float, fast_signature: tuple[tuple[str, int, int], ...]) -> bool:
    return cached.fast_signature == fast_signature and now - cached.validated_at < _validation_interval_seconds()


def get_image_bank_index(
    image_bank_path: Path | str | list | tuple | set = "image_bank",
    *,
    force_refresh: bool = False,
) -> ImageBankIndex:
    """Return a cached image-bank index, refreshing only when paths changed."""

    path_key = path_set_key(image_bank_path)
    now = time.monotonic()
    fast_signature = fast_paths_signature(path_key)

    with _INDEX_LOCK:
        cached = _INDEX_CACHE.get(path_key)
        if cached and not force_refresh and _cached_index_is_fresh(cached, now=now, fast_signature=fast_signature):
            return cached.index

    recursive_key = _recursive_cache_key(path_key)
    with _INDEX_LOCK:
        cached = _INDEX_CACHE.get(path_key)
        if cached and not force_refresh and cached.index.cache_key == recursive_key:
            cached.validated_at = now
            cached.fast_signature = fast_signature
            return cached.index

        index = build_image_bank_index(path_key, recursive_key)
        _INDEX_CACHE[path_key] = _CachedIndex(index, now, fast_signature)
        return index


def invalidate_image_bank_cache(image_bank_path: Path | str | list | tuple | set | None = None) -> None:
    """Clear all cached indexes, or only caches touching the supplied path set."""

    with _INDEX_LOCK:
        if image_bank_path is None:
            _INDEX_CACHE.clear()
            return
        requested = set(path_set_key(image_bank_path))
        for key in list(_INDEX_CACHE):
            if requested & set(key):
                _INDEX_CACHE.pop(key, None)


def scan_image_bank(
    image_bank_path: Path | str | list | tuple | set = "image_bank",
    *,
    force_refresh: bool = False,
) -> list[ImageCandidate]:
    """Return image candidates from the cached image-bank index."""

    return list(get_image_bank_index(image_bank_path, force_refresh=force_refresh).candidates)


_coerce_image_bank_paths = coerce_image_bank_paths
_path_set_key = path_set_key
_fast_paths_signature = fast_paths_signature
