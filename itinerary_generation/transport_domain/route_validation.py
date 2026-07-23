"""Validation for canonical transport route fields."""
from __future__ import annotations

import re

def _canonical_route_field_is_place(value: str) -> bool:
    """Reject parser route fields that still contain actions or service prose."""

    text = str(value or "").strip()
    if not text or len(text) > 70:
        return False
    lower = text.casefold()
    if re.match(
        r"^(?:drive|travel|continue|explore|visit|return|head|follow|enjoy|pick[- ]?up|drop[- ]?off|on\s+the|transfer\s+on)\b",
        lower,
    ):
        return False
    if lower in {"to", "from", "at", "on"}:
        return False
    if re.search(r"\b(?:next\s+day|same\s+day|arrival|departure|duration|travel\s+time)\b", lower):
        return False
    service_markers = (
        "self transfer",
        "transfer by",
        "car rental office",
        "rental car office",
        "activity upgrade",
        "transfer package",
    )
    if any(marker in lower for marker in service_markers):
        return False
    # Product and mode labels are not geographic endpoints. Transport hubs
    # remain valid because their terminal noun proves they are places.
    if re.search(r"\b(?:cruise|flight|train|rail(?:way)?|line|express|coach|bus|ferry|transfer)\b", lower) and not re.search(
        r"\b(?:airport|station|terminal|port|harbou?r|stop)\b", lower
    ):
        return False
    return True

