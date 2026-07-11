"""Resolve the physical mode of an arranged activity from source evidence.

Copy writers consume this contract instead of treating destination words such
as ``fjord`` as proof that an experience takes place on the water.  Strong
supplier transport evidence wins over scenic nouns in a product title.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


_WATER_PRODUCT_RE = re.compile(
    r"\b(?:fjord\s+cruise|sightseeing\s+cruise|boat\s+tour|boat\s+trip|electric\s+ship|"
    r"silent\s+ship|kayak(?:ing)?|paddl(?:e|ing)|sailing|catamaran|rib\s+(?:boat|safari))\b",
    re.IGNORECASE,
)
_ROAD_RE = re.compile(
    r"\b(?:mini[- ]?van|coach|bus|vehicle|car|drive|driving|road\s+trip|hotel\s+pick[- ]?up|"
    r"pick[- ]?up/drop[- ]?off|transportation\s+by)\b",
    re.IGNORECASE,
)
_WALK_RE = re.compile(r"\b(?:walking\s+tour|guided\s+walk|on\s+foot|hike|hiking)\b", re.IGNORECASE)
_FERRY_RE = re.compile(r"\b(?:ferry|round[- ]trip\s+ferry)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ActivityModeFacts:
    mode: str = "unknown"  # water | road | walking | mixed | unknown
    water_evidence: bool = False
    road_evidence: bool = False
    walking_evidence: bool = False
    ferry_evidence: bool = False

    @property
    def water_led(self) -> bool:
        return self.mode == "water"


def resolve_activity_mode(title: str = "", source_text: str = "") -> ActivityModeFacts:
    """Return mode facts without upgrading scenic place words into transport.

    ``fjord`` alone is geography, not water-mode evidence.  A ferry embedded in
    a broader excursion is treated as mixed unless the title itself is a ferry
    or cruise product.
    """

    title_text = " ".join(str(title or "").split())
    source = " ".join(str(source_text or "").split())
    combined = f"{title_text} {source}".strip()
    water = bool(_WATER_PRODUCT_RE.search(combined))
    road = bool(_ROAD_RE.search(combined))
    walking = bool(_WALK_RE.search(combined))
    ferry = bool(_FERRY_RE.search(combined))

    title_water = bool(_WATER_PRODUCT_RE.search(title_text))
    title_ferry = bool(_FERRY_RE.search(title_text))
    if title_water and not road:
        mode = "water"
    elif title_ferry and not (road or walking):
        mode = "water"
    elif road and (water or ferry or walking):
        mode = "mixed"
    elif walking and (water or ferry):
        mode = "mixed"
    elif road:
        mode = "road"
    elif walking:
        mode = "walking"
    elif water:
        mode = "water"
    elif ferry:
        mode = "mixed"
    else:
        mode = "unknown"
    return ActivityModeFacts(mode, water, road, walking, ferry)


__all__ = ["ActivityModeFacts", "resolve_activity_mode"]
