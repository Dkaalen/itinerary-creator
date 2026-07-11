"""Policy for labels that describe itinerary state rather than a place."""

from __future__ import annotations

import re


_NON_DESTINATION_EXACT = {
    "self explore",
    "self explored",
    "self-guided",
    "self guided",
    "extra day",
    "free time",
    "day at leisure",
    "at leisure",
}


def is_non_destination_label(value: object) -> bool:
    """Return true when a label is programme/service text, not geography."""

    text = re.sub(r"\s+", " ", str(value or "").strip()).casefold().strip(" -:|.,")
    if not text:
        return False
    if text in _NON_DESTINATION_EXACT:
        return True
    return bool(re.fullmatch(r"(?:day\s+)?\d*\s*(?:self[- ]?explor(?:e|ed)|free\s+time|at\s+leisure)", text))


__all__ = ["is_non_destination_label"]
