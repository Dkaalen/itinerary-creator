"""Priority helpers for effective itinerary row-type detection."""

from __future__ import annotations

import re

from itinerary_domain.row_type_rules import (
    has_numbered_bus_or_coach,
    looks_like_cruise_experience_text,
    looks_like_local_transfer,
    looks_like_long_distance_coach_or_bus,
    looks_like_pure_transport_activity,
)


_SOURCE_OWNED_TYPES = frozenset(
    {
        "Activity Upgrade",
        "Extra Hotel Night",
        "Group Tour",
        "Single Supplement Fee",
        "Transfer Package",
    }
)


def preserve_source_owned_type(normalized_item_type: str) -> str | None:
    """Keep explicit commercial/package types outside generic classification."""

    return normalized_item_type if normalized_item_type in _SOURCE_OWNED_TYPES else None


def preserve_explicit_overview(normalized_item_type: str) -> str | None:
    """Keep overview prose from being reclassified as transport."""

    return "Day Overview" if normalized_item_type == "Day Overview" else None


def activity_logistics_override(normalized_item_type: str, combined: str) -> str | None:
    """Return overrides for Activity rows that include logistics wording."""

    if normalized_item_type != "Activity":
        return None

    if any(marker in combined for marker in ("hop on", "hop-on", "hop off", "hop-off", "24 hrs ticket", "24 hour ticket")):
        return "Activity"
    if "stegastein" in combined and any(
        marker in combined for marker in ("electric minibus", "electric bus", "viewpoint", "sightseeing tour")
    ):
        return "Activity"
    if re.search(r"\btransfer\s+to\s+(?:glass\s+)?igloo\s+stay\b|\btransfer\s+to\s+[^.]{0,40}stay\b", combined, flags=re.IGNORECASE):
        return "Transfer"
    if any(
        marker in combined
        for marker in ("blue lagoon", "comfort ticket", "admission", "entry ticket", "return transfer")
    ) and any(marker in combined for marker in ("overview", "what's included", "what to expect", "ticket", "admission", "experience")):
        return "Activity"
    if "tallinn" in combined and any(marker in combined for marker in ("excursion", "guided tour", "self guided", "old town")):
        return "Activity"
    if looks_like_cruise_experience_text(combined):
        return "Activity"
    if looks_like_pure_transport_activity(combined):
        return "Transport"
    return None


def transfer_logistics_override(normalized_item_type: str, combined: str) -> str | None:
    """Return overrides for explicit Transfer rows."""

    if normalized_item_type != "Transfer":
        return None
    if re.search(r"\b(?:overnight|night)\s+train\b", combined, flags=re.IGNORECASE):
        return "Train"
    if looks_like_local_transfer(combined) and not looks_like_long_distance_coach_or_bus(combined) and not has_numbered_bus_or_coach(combined):
        return "Transfer"
    return None


def product_name_override(combined: str) -> str | None:
    """Return explicit named-product overrides."""

    if "norway in a nutshell" in combined:
        return "Transport"
    return None


def route_mode_override(normalized_item_type: str, combined: str) -> str | None:
    """Infer row type from clear route-mode wording."""

    route_mode_match = re.search(r"\b[a-zà-ÿøåäö .'-]+\s+to\s+[a-zà-ÿøåäö .'-]+\s+(train|flight|cruise|ferry|coach|bus)\b", combined)
    if route_mode_match and normalized_item_type in {"Transfer", "Transport", "Activity"} and "private" not in combined:
        mode = route_mode_match.group(1)
        if mode == "train":
            return "Train"
        if mode == "flight":
            return "Flight"
        if mode in {"cruise", "ferry"}:
            return "Cruise" if mode == "cruise" else "Ferry"
        return "Transport"

    if re.search(r"\b(?:day\s+|overnight\s+)?train\b[^\n|]{0,40}\b[a-zà-ÿøåäö .'-]+\s+-\s+[a-zà-ÿøåäö .'-]+", combined, flags=re.IGNORECASE):
        return "Train"
    if re.search(r"\bflight\b[^\n|]{0,40}\b[a-zà-ÿøåäö .'-]+\s+-\s+[a-zà-ÿøåäö .'-]+", combined, flags=re.IGNORECASE):
        return "Flight"
    return None


def direct_mode_override(combined: str) -> str | None:
    """Return type from direct mode phrases such as 'flight to'."""

    if (
        "flight to" in combined
        or combined.startswith("flight ")
        or re.search(r"\bflight\s*[:|]", combined)
        or re.search(r"\bflight\s+[a-zà-ÿøåäö\s]+\s+to\s+", combined)
    ):
        return "Flight"
    if (
        "train to" in combined
        or "train transfer" in combined
        or "express train" in combined
        or "overnight train" in combined
        or re.search(r"\btrain\s*[:|]", combined)
        or re.search(r"\btrain\s+[a-zà-ÿøåäö\s]+\s+to\s+", combined)
    ):
        return "Train"
    if "cruise to" in combined or "overnight cruise" in combined:
        return "Cruise"
    if "ferry to" in combined:
        return "Ferry"
    return None


def fallback_transport_override(normalized_item_type: str, combined: str) -> str | None:
    """Return final transport overrides after activity rows are protected."""

    if normalized_item_type == "Activity":
        return "Activity"
    if normalized_item_type == "Transfer" and looks_like_long_distance_coach_or_bus(combined) and "private" not in combined:
        return "Transport"
    if normalized_item_type == "Transfer" and looks_like_local_transfer(combined) and not looks_like_long_distance_coach_or_bus(combined) and not has_numbered_bus_or_coach(combined):
        return "Transfer"
    if ("coach transfer" in combined or combined.startswith("bus") or " bus " in f" {combined} ") and "private" not in combined:
        return "Transport"
    return None


__all__ = [
    "activity_logistics_override",
    "direct_mode_override",
    "fallback_transport_override",
    "preserve_explicit_overview",
    "preserve_source_owned_type",
    "product_name_override",
    "route_mode_override",
    "transfer_logistics_override",
]
