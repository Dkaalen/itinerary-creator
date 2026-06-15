"""Activity product fingerprint catalogue facade.

The public API stays here, while product-family rules live in focused modules.
That keeps fingerprinting source-first without one large renderer-facing rule
chain becoming a maintenance hotspot.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from itinerary_generation.activity_cache import (
    freeze_activity_row,
    freeze_activity_values,
    thaw_activity_row,
    thaw_activity_values,
)
from itinerary_generation.activity_product_core import (
    ActivityProductConfidence,
    ActivityProductFingerprint,
    match_product,
)
from itinerary_generation.activity_product_text import (
    activity_product_context,
    canonicalize_activity_text,
    extract_source_product_title,
)
from itinerary_generation.activity_product_rules import (
    match_iceland_activity,
    match_nordic_activity,
    match_norway_activity,
    match_scandinavia_activity,
)
from itinerary_generation.activity_training_catalogue import match_activity_training_entry

ActivityProductMatcher = Callable[[dict[str, Any] | None, str, str, str], ActivityProductFingerprint | None]

_PRODUCT_MATCHERS: tuple[ActivityProductMatcher, ...] = (
    match_norway_activity,
    match_nordic_activity,
    match_iceland_activity,
    match_scandinavia_activity,
)


@lru_cache(maxsize=4096)
def _fingerprint_activity_cached(
    row_snapshot: tuple[tuple[str, object], ...],
    values_snapshot: tuple[object, ...],
) -> ActivityProductFingerprint | None:
    row = thaw_activity_row(row_snapshot)
    values = thaw_activity_values(values_snapshot)
    source = activity_product_context(row, *values)
    source_lower = source.lower()
    if not source_lower:
        return None

    source_title = extract_source_product_title(row, *values)

    for matcher in _PRODUCT_MATCHERS:
        fingerprint = matcher(row, source, source_lower, source_title)
        if fingerprint:
            return fingerprint

    catalogue_entry = match_activity_training_entry(
        source,
        city=str(row.get("city", "") if row else ""),
        source_title=source_title,
    )
    if catalogue_entry:
        return match_product(
            catalogue_entry.canonical_family,
            catalogue_entry.product_type,
            catalogue_entry.display_title,
            source_title=source_title or catalogue_entry.display_title,
            variant_tags=("training_catalogue",),
        )

    return None


def fingerprint_activity(row: dict | None = None, *values: object) -> ActivityProductFingerprint | None:
    """Return a canonical activity fingerprint, cached by source-owned content."""

    return _fingerprint_activity_cached(
        freeze_activity_row(row),
        freeze_activity_values(values),
    )


def clear_activity_product_cache() -> None:
    """Clear in-process activity matching caches after catalogue/rule changes."""

    _fingerprint_activity_cached.cache_clear()


def activity_product_cache_info():
    return _fingerprint_activity_cached.cache_info()


__all__ = [
    "ActivityProductConfidence",
    "ActivityProductFingerprint",
    "activity_product_context",
    "activity_product_cache_info",
    "canonicalize_activity_text",
    "clear_activity_product_cache",
    "extract_source_product_title",
    "fingerprint_activity",
]
