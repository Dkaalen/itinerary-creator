"""Labelled supplier-detail extraction helpers."""
import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text

def _looks_like_cruise_experience_text(text: str) -> bool:
    """Return True when cruise wording describes a bookable experience.

    Supplier activity rows often contain route-shaped wording such as
    ``fjord cruise to Mostraumen``.  That should stay an Activity unless the
    row is clearly an overnight/point-to-point cruise or ferry transfer.
    """

    lower = str(text or "").lower()
    if not lower or "cruise" not in lower:
        return False

    if re.search(r"\b(?:overnight|night|coastal|atlantic ocean)\s+cruise\b", lower):
        return False
    if re.search(r"\bcruise\s+(?:from\s+)?[a-zà-ÿøåäö .'-]+\s+to\s+[a-zà-ÿøåäö .'-]+\b", lower) and not any(
        marker in lower
        for marker in ["round-trip", "round trip", "return", "day trip", "sightseeing", "fjord", "canal", "archipelago"]
    ):
        return False

    experience_markers = [
        "fjord cruise",
        "sightseeing cruise",
        "cruise day trip",
        "day cruise",
        "canal cruise",
        "archipelago cruise",
        "wildlife cruise",
        "northern lights cruise",
        "icebreaker cruise",
        "dinner cruise",
        "private cruise",
        "boat tour",
        "catamaran",
        "rib safari",
        "sea eagle",
        "oslofjord",
        "oslo fjord",
        "nærøyfjord",
        "naeroyfjord",
        "mostraumen",
        "geirangerfjord",
        "geiranger fjord",
        "trollfjord",
    ]
    if any(marker in lower for marker in experience_markers):
        return True

    # Labelled activity metadata strongly implies the cruise is an excursion,
    # not a location-changing transport row.
    return bool(re.search(r"\b(?:time|duration|meeting point|includes?|description)\s*:", lower))


def extract_detail(text, label):
    """Extract a labelled detail section, matching labels case-insensitively.

    Supplier rows are not consistent about label casing, for example
    ``Notable sights:`` vs ``Notable Sights:``.  The previous exact-string
    extraction missed those sections and let later metadata leak into fields
    such as the meeting point.
    """

    source = str(text or "")
    label_pattern = re.compile(rf"\b{re.escape(label)}\s*:", flags=re.IGNORECASE)
    match = label_pattern.search(source)
    if not match:
        return ""

    after_marker = source[match.end():]
    stop_labels = [re.escape(item) for item in DETAIL_LABELS if item.lower() != str(label).lower()]
    stop_labels.extend([
        r"what[’']?s\s+included",
        r"what\s+is\s+included",
        r"what\s+to\s+expect",
        r"overview",
        r"please\s+note",
        r"important\s+information",
        r"pick[-\s]*up\s*/\s*meeting\s*point",
        r"meeting\s+point",
    ])
    if stop_labels:
        # Stop on both dash-separated metadata (" - Includes:") and supplier
        # block labels on their own line or after a pasted sentence.  Without
        # this, labels such as "What's included?" can leak into meeting points.
        stop_pattern = re.compile(
            rf"(?:\s+-\s+|\n+\s*|\s{{2,}})(?:{'|'.join(stop_labels)})\s*(?::|\?|(?=\s|[A-ZÀ-ÖØ-Þ]))",
            flags=re.IGNORECASE,
        )
        stop_match = stop_pattern.search(after_marker)
        if stop_match:
            after_marker = after_marker[:stop_match.start()]

    return after_marker.strip(" -")


def extract_between_markers(text, start_patterns, stop_patterns):
    """
    Extract a section from long supplier-style descriptions.

    Used for colleague paste formats where cells contain blocks like:
    What's included?
    item
    item
    Pick up / meeting point
    address
    """

    if not text:
        return ""

    lowered = text.lower()
    starts = []

    for pattern in start_patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            starts.append(match.end())

    if not starts:
        return ""

    start = min(starts)
    section = text[start:]

    stop_positions = []
    section_lower = section.lower()

    for pattern in stop_patterns:
        match = re.search(pattern, section_lower, flags=re.IGNORECASE)
        if match:
            stop_positions.append(match.start())

    if stop_positions:
        section = section[:min(stop_positions)]

    return section.strip(" :|-\n\r\t")
