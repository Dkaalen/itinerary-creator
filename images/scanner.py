"""Image-bank path handling, indexing and cached scanning.

The image bank is effectively read-only during a normal editing session.  The
old cache still performed a recursive directory walk before every cache lookup,
which made nominal cache hits expensive.  This module keeps a persistent,
content-addressed index in memory and validates it periodically.  App-managed
uploads explicitly invalidate the index, so normal interactions reuse metadata
without sacrificing correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import os
from pathlib import Path
from threading import RLock
import time

import diagnostics

from .metadata import IMAGE_EXTENSIONS, ImageCandidate, city_variants, extract_image_metadata, normalize_keyword


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
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
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


def _resolved_path_text(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _path_set_key(image_bank_path: Path | str | list | tuple | set = "image_bank") -> tuple[str, ...]:
    return tuple(_resolved_path_text(path) for path in coerce_image_bank_paths(image_bank_path))


def _fast_paths_signature(path_key: tuple[str, ...]) -> tuple[tuple[str, int, int], ...]:
    """Return a cheap root-level signature used between full validations."""

    signature: list[tuple[str, int, int]] = []
    for path_text in path_key:
        path = Path(path_text)
        stat = _stat_signature(path) if path.exists() else None
        signature.append((path_text, *(stat or (0, 0))))
    return tuple(signature)


def _scan_cache_key(image_bank_path: Path | str | list | tuple | set = "image_bank") -> tuple[tuple[str, int, int, int, str], ...]:
    """Return a recursive content signature for image-bank scans.

    This remains the authoritative validation key and intentionally includes
    nested file sizes and mtimes.  It is no longer rebuilt before every cached
    lookup; :func:`get_image_bank_index` performs it only when the validation
    interval expires or a root-level change is detected.
    """

    key = []
    for base in coerce_image_bank_paths(image_bank_path):
        resolved = Path(_resolved_path_text(base))
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
    candidates: list[ImageCandidate] = []
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


@dataclass(slots=True)
class ImageBankIndex:
    """Reusable metadata index for matching, audit and replacement workflows."""

    paths: tuple[str, ...]
    cache_key: tuple[tuple[str, int, int, int, str], ...]
    candidates: tuple[ImageCandidate, ...]
    by_path: dict[str, ImageCandidate]
    by_city_variant: dict[str, tuple[ImageCandidate, ...]]
    defaults: tuple[ImageCandidate, ...]
    destination_candidates: tuple[ImageCandidate, ...]
    destination_roots: tuple[str, ...]
    countries: tuple[str, ...]
    destinations: tuple[str, ...]
    by_root: dict[str, tuple[ImageCandidate, ...]]
    order_by_path: dict[str, int]

    def candidates_for_city(self, city: str, *, include_defaults: bool = True) -> tuple[ImageCandidate, ...]:
        keys = city_variants(city)
        return self._candidate_union(keys, include_defaults=include_defaults)

    def candidates_for_context(self, context: dict, *, include_defaults: bool = True) -> tuple[ImageCandidate, ...]:
        keys = {normalize_keyword(value) for value in context.get("city_variants", set()) if normalize_keyword(value)}
        return self._candidate_union(keys, include_defaults=include_defaults)

    def root_candidates(self, root: Path | str) -> tuple[ImageCandidate, ...]:
        return self.by_root.get(_resolved_path_text(Path(root)), ())

    def _candidate_union(self, keys: set[str], *, include_defaults: bool) -> tuple[ImageCandidate, ...]:
        selected: dict[str, ImageCandidate] = {}
        for key in keys:
            for candidate in self.by_city_variant.get(key, ()):
                selected.setdefault(_resolved_path_text(Path(candidate.path)), candidate)
        if include_defaults:
            for candidate in self.defaults:
                selected.setdefault(_resolved_path_text(Path(candidate.path)), candidate)
        return tuple(sorted(selected.values(), key=lambda candidate: self.order_by_path.get(_resolved_path_text(Path(candidate.path)), 0)))


@dataclass(slots=True)
class _CachedIndex:
    index: ImageBankIndex
    validated_at: float
    fast_signature: tuple[tuple[str, int, int], ...]


_INDEX_CACHE: dict[tuple[str, ...], _CachedIndex] = {}
_INDEX_LOCK = RLock()


def _validation_interval_seconds() -> float:
    raw = os.environ.get("ITINERARY_IMAGE_INDEX_VALIDATE_SECONDS", "30")
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 30.0


def _candidate_root(candidate: ImageCandidate, roots: tuple[str, ...]) -> str:
    candidate_path = Path(candidate.path)
    try:
        candidate_resolved = candidate_path.resolve()
    except OSError:
        candidate_resolved = candidate_path
    for root_text in roots:
        root = Path(root_text)
        try:
            if candidate_resolved.is_relative_to(root.resolve()):
                return root_text
        except (OSError, ValueError):
            continue
    return ""


def _build_image_bank_index(
    paths: tuple[str, ...],
    cache_key: tuple[tuple[str, int, int, int, str], ...],
) -> ImageBankIndex:
    candidates = _scan_image_bank_cached(cache_key)
    by_path: dict[str, ImageCandidate] = {}
    city_lists: dict[str, list[ImageCandidate]] = {}
    default_candidates: list[ImageCandidate] = []
    destination_candidates: list[ImageCandidate] = []
    root_lists: dict[str, list[ImageCandidate]] = {path: [] for path in paths}
    order_by_path: dict[str, int] = {}

    for index, candidate in enumerate(candidates):
        path_key = _resolved_path_text(Path(candidate.path))
        by_path[path_key] = candidate
        order_by_path[path_key] = index
        candidate_city_keys = city_variants(candidate.city)
        if normalize_keyword(candidate.city) in {"default", "defoult"}:
            default_candidates.append(candidate)
        else:
            destination_candidates.append(candidate)
        for city_key in candidate_city_keys:
            city_lists.setdefault(city_key, []).append(candidate)
        root = _candidate_root(candidate, paths)
        if root:
            root_lists.setdefault(root, []).append(candidate)

    return ImageBankIndex(
        paths=paths,
        cache_key=cache_key,
        candidates=candidates,
        by_path=by_path,
        by_city_variant={key: tuple(values) for key, values in city_lists.items()},
        defaults=tuple(default_candidates),
        destination_candidates=tuple(destination_candidates),
        destination_roots=tuple(
            root for root, values in root_lists.items()
            if any(normalize_keyword(candidate.city) not in {"default", "defoult"} for candidate in values)
        ),
        countries=tuple(sorted({str(candidate.country).strip() for candidate in destination_candidates if str(candidate.country).strip()})),
        destinations=tuple(sorted({str(candidate.city).strip() for candidate in destination_candidates if str(candidate.city).strip()})),
        by_root={key: tuple(values) for key, values in root_lists.items()},
        order_by_path=order_by_path,
    )


def get_image_bank_index(
    image_bank_path: Path | str | list | tuple | set = "image_bank",
    *,
    force_refresh: bool = False,
) -> ImageBankIndex:
    """Return the persistent image-bank index for the supplied roots."""

    path_key = _path_set_key(image_bank_path)
    now = time.monotonic()
    fast_signature = _fast_paths_signature(path_key)
    interval = _validation_interval_seconds()

    with _INDEX_LOCK:
        cached = _INDEX_CACHE.get(path_key)
        if (
            cached
            and not force_refresh
            and cached.fast_signature == fast_signature
            and (now - cached.validated_at) < interval
        ):
            return cached.index

    recursive_key = _scan_cache_key([Path(path) for path in path_key])

    with _INDEX_LOCK:
        cached = _INDEX_CACHE.get(path_key)
        if cached and not force_refresh and cached.index.cache_key == recursive_key:
            cached.validated_at = now
            cached.fast_signature = fast_signature
            return cached.index

        index = _build_image_bank_index(path_key, recursive_key)
        _INDEX_CACHE[path_key] = _CachedIndex(index=index, validated_at=now, fast_signature=fast_signature)
        return index


def invalidate_image_bank_cache(image_bank_path: Path | str | list | tuple | set | None = None) -> None:
    """Invalidate image metadata after app-managed uploads or bank refreshes."""

    with _INDEX_LOCK:
        if image_bank_path is None:
            _INDEX_CACHE.clear()
            return
        requested = set(_path_set_key(image_bank_path))
        for key in list(_INDEX_CACHE):
            if requested & set(key):
                _INDEX_CACHE.pop(key, None)


def scan_image_bank(
    image_bank_path: Path | str | list | tuple | set = "image_bank",
    *,
    force_refresh: bool = False,
) -> list[ImageCandidate]:
    return list(get_image_bank_index(image_bank_path, force_refresh=force_refresh).candidates)


# Backwards-compatible private alias for callers/tests that may have imported it.
_coerce_image_bank_paths = coerce_image_bank_paths
