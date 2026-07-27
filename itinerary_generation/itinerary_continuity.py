"""Authoritative itinerary schedule and geographic-continuity API.

This module is the public continuity owner used by generation, structured
documents, quality, preview, editor, and PDF preparation. Focused private
modules calculate row facts, findings, and day-state projection; this owner
assembles them once without rewriting source rows or customer copy.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from itinerary_generation.itinerary_continuity_facts import _group_rows, _included_rows
from itinerary_generation.itinerary_continuity_findings import (
    _accommodation_overlap_findings,
    _geographic_findings,
    _overlap_findings,
)
from itinerary_generation.itinerary_continuity_models import (
    ERROR,
    WARNING,
    ContinuityFinding,
    DayContinuityState,
    ItineraryContinuityReport,
)
from itinerary_generation.itinerary_continuity_state import _build_day_states


def build_itinerary_continuity_report(
    rows: Iterable[Mapping[str, object]] | None,
) -> ItineraryContinuityReport:
    """Return the canonical continuity findings and per-day decisions."""

    included = _included_rows(rows)
    grouped = _group_rows(included)
    findings = _overlap_findings(grouped)
    findings.extend(_accommodation_overlap_findings(included))
    findings.extend(_geographic_findings(grouped))
    return ItineraryContinuityReport(
        findings=tuple(findings),
        days=_build_day_states(grouped),
    )


def evaluate_itinerary_continuity(
    rows: Iterable[Mapping[str, object]] | None,
) -> tuple[ContinuityFinding, ...]:
    """Return deterministic schedule and route-continuity findings.

    Optional and excluded rows do not participate. Self-arranged transport is
    retained because it is valid continuity evidence even when excluded from
    arranged pricing.
    """

    return build_itinerary_continuity_report(rows).findings


__all__ = [
    "ERROR",
    "WARNING",
    "ContinuityFinding",
    "DayContinuityState",
    "ItineraryContinuityReport",
    "build_itinerary_continuity_report",
    "evaluate_itinerary_continuity",
]
