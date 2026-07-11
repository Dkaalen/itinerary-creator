"""Canonical activity identity contract.

This module owns the client-facing identity selected for one arranged activity.
Title, description, render, and QA layers consume this contract instead of
independently re-classifying the same supplier row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from itinerary_generation.activity_product_titles import activity_product_metadata
from itinerary_generation.product_rules import find_product_match
from itinerary_generation.supplier_cleanup_brain import clean_supplier_title
from text_polish import polish_title


@dataclass(frozen=True)
class ActivityIdentity:
    """Resolved identity shared by activity title and description decisions."""

    source_title: str = ""
    canonical_family: str = ""
    product_type: str = ""
    display_title: str = ""
    confidence: str = "weak"
    warnings: tuple[str, ...] = ()
    source: str = "fallback"

    @property
    def is_strong(self) -> bool:
        return self.confidence == "strong"


def _clean_title(value: object) -> str:
    return clean_supplier_title(polish_title(str(value or "").strip())).strip(" -:|.,")


def _source_title(row: Mapping[str, object]) -> str:
    for key in ("original_title", "title"):
        title = _clean_title(row.get(key))
        if title:
            return title
    return ""


def resolve_activity_identity(row: Mapping[str, object]) -> ActivityIdentity:
    """Return the one canonical identity for an activity row.

    Normalized product metadata is strongest.  Registry matches are next.  A
    cleaned supplier title is the final source-backed fallback.  No layer is
    allowed to upgrade weak evidence to a confident named product.
    """

    metadata = activity_product_metadata(row)
    source_title = _source_title(row)
    if metadata:
        display_title = _clean_title(metadata.get("display_title")) or source_title
        warnings = tuple(str(item) for item in (metadata.get("warnings") or ()) if str(item).strip())
        return ActivityIdentity(
            source_title=source_title,
            canonical_family=str(metadata.get("canonical_family") or "").strip(),
            product_type=str(metadata.get("product_type") or "").strip(),
            display_title=display_title,
            confidence=str(metadata.get("confidence") or "strong").strip() or "strong",
            warnings=warnings,
            source="normalized_product",
        )

    match = find_product_match(dict(row))
    if match:
        warnings = tuple(item for item in (match.warning_code, match.warning_message) if item)
        return ActivityIdentity(
            source_title=source_title,
            canonical_family=match.rule_id,
            product_type="",
            display_title=_clean_title(match.title) or source_title,
            confidence=match.confidence,
            warnings=warnings,
            source="product_registry",
        )

    return ActivityIdentity(
        source_title=source_title,
        display_title=source_title or "Experience",
        confidence="weak",
        warnings=("fallback_activity_identity",) if not source_title else (),
        source="supplier_title" if source_title else "fallback",
    )


__all__ = ["ActivityIdentity", "resolve_activity_identity"]
