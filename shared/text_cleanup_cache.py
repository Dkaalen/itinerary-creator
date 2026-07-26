"""Cache controls and metrics for deterministic text-cleanup hot paths.

The cleanup rules are static for the lifetime of a process.  These helpers are
kept outside the hot path and are intended for benchmarks, tests, and explicit
operational diagnostics.
"""

from __future__ import annotations

from shared.source_text_cleanup import _fix_common_text_cached
from place_alias_queries import _normalize_place_text_cached
from text_polish_modules.text_cleanup import _polish_text_fragment


def clear_text_cleanup_caches() -> None:
    """Clear all bounded text-cleanup caches."""

    _fix_common_text_cached.cache_clear()
    _normalize_place_text_cached.cache_clear()
    _polish_text_fragment.cache_clear()


def text_cleanup_cache_snapshot() -> dict[str, dict[str, int | None]]:
    """Return serializable cache metrics for profiling and diagnostics."""

    return {
        "fix_common_text": _fix_common_text_cached.cache_info()._asdict(),
        "normalize_place_text": _normalize_place_text_cached.cache_info()._asdict(),
        "polish_text_fragment": _polish_text_fragment.cache_info()._asdict(),
    }
