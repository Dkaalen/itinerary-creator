"""Helpers for consuming normalized activity-product display titles."""

from __future__ import annotations

from collections.abc import Mapping


def activity_product_metadata(row: Mapping[str, object]) -> Mapping[str, object]:
    """Return normalized activity-product metadata attached by the normalizer."""

    metadata = row.get("activity_product")
    return metadata if isinstance(metadata, Mapping) else {}


def activity_product_display_title(row: Mapping[str, object]) -> str:
    """Return the normalized product display title already attached to a row."""

    return str(activity_product_metadata(row).get("display_title") or "").strip()


def activity_product_family(row: Mapping[str, object]) -> str:
    """Return the canonical activity-product family attached by the normalizer."""

    return str(activity_product_metadata(row).get("canonical_family") or "").strip()


__all__ = ["activity_product_display_title", "activity_product_family", "activity_product_metadata"]
