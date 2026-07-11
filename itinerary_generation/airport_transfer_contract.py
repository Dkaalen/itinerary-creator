"""Direction contract for local airport transfers.

Airport-transfer direction is factual input used by Day Intent, timeline events,
and copy.  It is resolved once here so those layers cannot disagree about
whether a transfer is an arrival or a departure.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


@dataclass(frozen=True)
class AirportTransferFacts:
    is_airport_transfer: bool = False
    direction: str = ""  # arrival | departure | unknown
    evidence: str = ""


def _segments(row: Mapping[str, object] | str) -> tuple[str, ...]:
    if isinstance(row, str):
        return (" ".join(row.split()).casefold(),)
    return tuple(
        " ".join(str(row.get(key) or "").split()).casefold()
        for key in ("title", "original_title", "details", "raw")
        if str(row.get(key) or "").strip()
    )


def _segment_direction(text: str) -> tuple[str, str]:
    if "airport" not in text and "flight terminal" not in text:
        return "", ""
    stay = r"(?:hotel|accommodation|city\s+centre|city\s+center|resort|lodge)"
    airport = r"(?:airport|flight terminal)"
    if re.search(rf"\b{stay}\b.{{0,80}}\bto\b.{{0,80}}\b(?:the\s+)?{airport}\b", text):
        return "departure", "stay_to_airport"
    if re.search(rf"\b{airport}\b.{{0,80}}\bto\b.{{0,80}}\b{stay}\b", text):
        return "arrival", "airport_to_stay"
    if re.search(rf"\bto\s+(?:the\s+)?(?:[a-zà-ÿ .'-]+\s+)?{airport}\b", text):
        return "departure", "to_airport"
    if re.search(rf"\bfrom\s+(?:the\s+)?{airport}\b|\b{airport}\b\s+to\b", text):
        return "arrival", "from_airport"
    if "arrival transfer" in text or "airport pick-up" in text or "airport pickup" in text:
        return "arrival", "arrival_marker"
    if "departure transfer" in text or "airport drop-off" in text or "airport drop off" in text:
        return "departure", "departure_marker"
    return "unknown", "airport_without_direction"


def airport_transfer_facts(row: Mapping[str, object] | str) -> AirportTransferFacts:
    directions = [_segment_direction(segment) for segment in _segments(row)]
    directions = [item for item in directions if item[0]]
    if not directions:
        return AirportTransferFacts()
    for desired in ("departure", "arrival"):
        for direction, evidence in directions:
            if direction == desired:
                return AirportTransferFacts(True, direction, evidence)
    return AirportTransferFacts(True, "unknown", directions[0][1])


__all__ = ["AirportTransferFacts", "airport_transfer_facts"]
