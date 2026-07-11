"""Core activity product fingerprint types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ActivityProductConfidence = Literal["strong", "weak"]


@dataclass(frozen=True)
class ActivityProductFingerprint:
    """Canonical identity for one supplier activity product."""

    canonical_family: str
    product_type: str
    display_title: str
    confidence: ActivityProductConfidence = "strong"
    source_title: str = ""
    variant_tags: tuple[str, ...] = ()
    route_legs: tuple[dict[str, str], ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def as_row_metadata(self) -> dict[str, Any]:
        return {
            "canonical_family": self.canonical_family,
            "product_type": self.product_type,
            "display_title": self.display_title,
            "confidence": self.confidence,
            "source_title": self.source_title,
            "variant_tags": list(self.variant_tags),
            "route_legs": [dict(leg) for leg in self.route_legs],
            "warnings": list(self.warnings),
        }


def match_product(
    canonical_family: str,
    product_type: str,
    title: str,
    *,
    source_title: str = "",
    variant_tags: tuple[str, ...] = (),
    route_legs: tuple[dict[str, str], ...] = (),
    confidence: ActivityProductConfidence = "strong",
    warnings: tuple[str, ...] = (),
) -> ActivityProductFingerprint:
    """Create a normalized product fingerprint."""

    return ActivityProductFingerprint(
        canonical_family=canonical_family,
        product_type=product_type,
        display_title=title,
        confidence=confidence,
        source_title=source_title or title,
        variant_tags=variant_tags,
        route_legs=route_legs,
        warnings=warnings,
    )
