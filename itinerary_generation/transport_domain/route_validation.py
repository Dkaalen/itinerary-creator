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
        r"^(?:drive|travel|continue|explore|visit|return|head|follow|enjoy|pick[- ]?up|drop[- ]?off)\b",
        lower,
    ):
        return False
    service_markers = (
        "self transfer",
        "transfer by",
        "car rental office",
        "rental car office",
        "activity upgrade",
        "transfer package",
    )
    return not any(marker in lower for marker in service_markers)

