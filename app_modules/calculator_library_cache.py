"""Cache Local Library reads for the calculator UI."""

from __future__ import annotations

from time import monotonic
from typing import Any, Callable, MutableMapping

from calculator.library_store import LocalLibraryReadResult, LocalLibraryStore

CALCULATOR_LIBRARY_CACHE_KEY = "calculator_library_read_result"
CALCULATOR_LIBRARY_CACHE_TIME_KEY = "calculator_library_read_time"
DEFAULT_LIBRARY_CACHE_TTL_SECONDS = 300.0

LibraryReader = Callable[[], LocalLibraryReadResult]


def read_cached_local_library(
    session_state: MutableMapping[str, Any],
    *,
    ttl_seconds: float = DEFAULT_LIBRARY_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
    reader: LibraryReader | None = None,
) -> LocalLibraryReadResult:
    """Return cached Local Library rows, refreshing when the cache is stale."""

    cached = session_state.get(CALCULATOR_LIBRARY_CACHE_KEY)
    cached_at = _float_value(session_state.get(CALCULATOR_LIBRARY_CACHE_TIME_KEY))
    if not force_refresh and isinstance(cached, LocalLibraryReadResult) and _cache_is_fresh(cached_at, ttl_seconds):
        return cached

    result = (reader or LocalLibraryStore().list_rows)()
    session_state[CALCULATOR_LIBRARY_CACHE_KEY] = result
    session_state[CALCULATOR_LIBRARY_CACHE_TIME_KEY] = monotonic()
    return result


def clear_cached_local_library(session_state: MutableMapping[str, Any]) -> None:
    """Forget cached Local Library rows."""

    session_state.pop(CALCULATOR_LIBRARY_CACHE_KEY, None)
    session_state.pop(CALCULATOR_LIBRARY_CACHE_TIME_KEY, None)


def _cache_is_fresh(cached_at: float, ttl_seconds: float) -> bool:
    if cached_at <= 0:
        return False
    return monotonic() - cached_at <= max(0.0, ttl_seconds)


def _float_value(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
