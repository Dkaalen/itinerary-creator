"""Small reusable rule predicates for effective row-type detection."""

from __future__ import annotations

import re

LONG_DISTANCE_COACH_MARKERS = (
    "coach transfer",
    "panorama coach",
    "panoramic coach",
)
PURE_TRANSPORT_ACTIVITY_MARKERS = (
    "arctic route coach transfer",
    "coach transfer",
    "bus transfer",
    "shuttle transfer",
    "airport transfer",
    "transfer to airport",
    "transfer from",
)
ACTIVITY_EXPERIENCE_MARKERS = (
    "guided tour",
    "sightseeing",
    "city tour",
    "walking tour",
    "day trip",
    "excursion",
    "northern lights",
    "aurora",
    "fjord",
    "cruise",
    "safari",
    "hike",
    "museum",
    "lagoon",
    "village",
    "reindeer",
    "husky",
    "whale",
)
LOCAL_TRANSFER_MARKERS = (
    "self transfer",
    "self-arranged transfer",
    "self-guided transfer",
    "private",
    "hotel to",
    "airport to",
    "station to",
    "to hotel",
    "to airport",
    "to station",
    "to railway station",
    "to train station",
    "accommodation",
    "bus station",
    "bustation",
)


def looks_like_long_distance_coach_or_bus(combined: str) -> bool:
    """Return True for arranged coach/bus transport, not local transfers."""

    return bool(
        re.search(r"\b(?:bus|coach)\s*[:|]", combined)
        or any(marker in combined for marker in LONG_DISTANCE_COACH_MARKERS)
        or ("long distance" in combined and ("coach" in combined or "bus" in combined))
    )


def looks_like_pure_transport_activity(combined: str) -> bool:
    """Return True when an Activity-typed row is clearly only transport."""

    return any(marker in combined for marker in PURE_TRANSPORT_ACTIVITY_MARKERS) and not any(
        marker in combined for marker in ACTIVITY_EXPERIENCE_MARKERS
    )


def looks_like_local_transfer(combined: str) -> bool:
    """Return True for local/private/self transfer wording."""

    return any(marker in combined for marker in LOCAL_TRANSFER_MARKERS)


def has_numbered_bus_or_coach(combined: str) -> bool:
    return bool(re.search(r"\b(bus|coach)\s*\d+\b", combined))


__all__ = [
    "ACTIVITY_EXPERIENCE_MARKERS",
    "LOCAL_TRANSFER_MARKERS",
    "LONG_DISTANCE_COACH_MARKERS",
    "PURE_TRANSPORT_ACTIVITY_MARKERS",
    "has_numbered_bus_or_coach",
    "looks_like_local_transfer",
    "looks_like_long_distance_coach_or_bus",
    "looks_like_pure_transport_activity",
]
