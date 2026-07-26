"""Labelled supplier-detail extraction helpers."""
import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from shared.source_time import normalize_duration_text, normalize_time_text


def extract_detail(text, label):
    """Extract a labelled detail section, matching labels case-insensitively.

    Supplier rows are not consistent about label casing, for example
    ``Notable sights:`` vs ``Notable Sights:``.  The previous exact-string
    extraction missed those sections and let later metadata leak into fields
    such as the meeting point.
    """

    source = str(text or "")
    label_pattern = re.compile(rf"\b{re.escape(label)}\s*:", flags=re.IGNORECASE)
    matches = label_pattern.finditer(source)
    match = next(
        (candidate for candidate in matches if not (str(label).casefold() == "time" and re.search(r"driving\s*$", source[: candidate.start()], flags=re.IGNORECASE))),
        None,
    )
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
