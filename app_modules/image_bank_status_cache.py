"""Session-scoped image-bank status cache.

Image-bank status scans touch the runtime image bank and can be requested several
 times during a single Streamlit rerun.  This helper keeps those scans keyed by
 the itinerary's required-destination signature and the current image-bank
 storage signature, so picture/export screens can reuse status without going
 stale after a bank reconnect or content change.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping, MutableMapping

CACHE_KEY = "_image_bank_status_cache"


def image_request_signature(required_destinations: Iterable[Any] | None) -> str:
    """Return a deterministic cache signature for destination image requests."""

    normalized = []
    for item in required_destinations or []:
        if isinstance(item, Mapping):
            normalized.append({str(key): str(value or "") for key, value in sorted(item.items())})
        else:
            normalized.append(str(item or ""))
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def image_bank_storage_signature_from_status(status: Mapping[str, Any] | None) -> str:
    """Return a deterministic signature for image-bank storage metadata."""

    status = status or {}
    payload = {
        "paths": [str(path) for path in status.get("paths", []) or []],
        "existing_paths": [str(path) for path in status.get("existing_paths", []) or []],
        "source_path": str(status.get("source_path", "") or ""),
        "destination_source_paths": [str(path) for path in status.get("destination_source_paths", []) or []],
        "destination_image_count": int(status.get("destination_image_count", 0) or 0),
        "default_image_count": int(status.get("default_image_count", 0) or 0),
        "total_image_count": int(status.get("total_image_count", 0) or 0),
        "countries_found": [str(value) for value in status.get("countries_found", []) or []],
        "destinations_found": [str(value) for value in status.get("destinations_found", []) or []],
        "repo_url": str(status.get("repo_url", "") or ""),
        "branch": str(status.get("branch", "") or ""),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def get_cached_image_bank_status(
    state: MutableMapping[str, Any],
    required_destinations: Iterable[Any] | None,
    status_func: Callable[[Iterable[Any] | None], Mapping[str, Any]],
    *,
    bank_signature: str | None = None,
) -> dict[str, Any]:
    """Return cached status for *required_destinations*, computing it on miss."""

    request_signature = image_request_signature(required_destinations)
    cache = state.get(CACHE_KEY)
    expected_bank_signature = bank_signature
    if (
        isinstance(cache, Mapping)
        and cache.get("request_signature") == request_signature
        and (expected_bank_signature is None or cache.get("bank_signature") == expected_bank_signature)
        and isinstance(cache.get("status"), Mapping)
    ):
        return dict(cache["status"])

    status = dict(status_func(required_destinations))
    resolved_bank_signature = bank_signature or image_bank_storage_signature_from_status(status)
    state[CACHE_KEY] = {
        "request_signature": request_signature,
        "bank_signature": resolved_bank_signature,
        "status": status,
    }
    return dict(status)


def store_image_bank_status(
    state: MutableMapping[str, Any],
    required_destinations: Iterable[Any] | None,
    status: Mapping[str, Any],
    *,
    bank_signature: str | None = None,
) -> dict[str, Any]:
    """Store a freshly repaired/connected status and return it as a plain dict."""

    value = dict(status or {})
    state[CACHE_KEY] = {
        "request_signature": image_request_signature(required_destinations),
        "bank_signature": bank_signature or image_bank_storage_signature_from_status(value),
        "status": value,
    }
    return dict(value)


def clear_image_bank_status_cache(state: MutableMapping[str, Any]) -> None:
    """Invalidate the cached image-bank status."""

    state.pop(CACHE_KEY, None)
