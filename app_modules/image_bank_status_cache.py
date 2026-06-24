"""Session-scoped image-bank status cache.

Image-bank status scans touch the runtime image bank and can be requested several
 times during a single Streamlit rerun.  This helper keeps those scans keyed by
 the itinerary's required-destination signature while staying easy to invalidate
 after a connection/repair attempt.
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


def get_cached_image_bank_status(
    state: MutableMapping[str, Any],
    required_destinations: Iterable[Any] | None,
    status_func: Callable[[Iterable[Any] | None], Mapping[str, Any]],
) -> dict[str, Any]:
    """Return cached status for *required_destinations*, computing it on miss."""

    signature = image_request_signature(required_destinations)
    cache = state.get(CACHE_KEY)
    if isinstance(cache, Mapping) and cache.get("signature") == signature and isinstance(cache.get("status"), Mapping):
        return dict(cache["status"])

    status = dict(status_func(required_destinations))
    state[CACHE_KEY] = {"signature": signature, "status": status}
    return dict(status)


def store_image_bank_status(
    state: MutableMapping[str, Any],
    required_destinations: Iterable[Any] | None,
    status: Mapping[str, Any],
) -> dict[str, Any]:
    """Store a freshly repaired/connected status and return it as a plain dict."""

    value = dict(status or {})
    state[CACHE_KEY] = {"signature": image_request_signature(required_destinations), "status": value}
    return dict(value)


def clear_image_bank_status_cache(state: MutableMapping[str, Any]) -> None:
    """Invalidate the cached image-bank status."""

    state.pop(CACHE_KEY, None)
