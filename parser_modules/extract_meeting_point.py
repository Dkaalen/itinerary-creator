"""Meeting-point extraction helpers for supplier activity text."""

from __future__ import annotations

import re

from parser_modules.common import clean_space
from parser_modules.details import extract_between_markers, extract_detail


def truncate_meeting_point_metadata(value: str) -> str:
    """Keep only the address/logistics part of a meeting-point field."""

    text = clean_space(value)
    if not text:
        return ""

    # Supplier rows often put "Meeting point: address What's included? ..."
    # on one line. Keep only the address/logistics before later metadata.
    text = re.split(
        r"\s*(?=(?:what[’']?s\s+included|what\s+to\s+expect|overview|highlights?|itinerary|packages|please\s+note|important\s+information)\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    # Pipe-style activity cells commonly continue after the meeting point with
    # inclusions: "Pick up / meeting point, Office | Pick-up/drop-off, guide".
    # Do not let the following inclusion segment become part of the address.
    text = re.split(
        r"\s*\|\s*(?=(?:pick[- ]?up/drop[- ]?off|pick[- ]?up|pickup|drop[- ]?off|professional|english|knowledgeable|winter|warm|snacks?|drinks?|included|includes?)\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    text = re.sub(
        r"^(?:pick[- ]?up\s*/\s*meeting\s*point|pickup\s*/\s*meeting\s*point|meeting\s*point)\s*[,;:|-]*\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return clean_space(text).strip(" ,;:|-")


def extract_meeting_point_from_description(main_text: str) -> str:
    """Extract a meeting point without swallowing downstream metadata."""

    standard_meeting = extract_detail(main_text, "Meeting point")

    if standard_meeting:
        return truncate_meeting_point_metadata(standard_meeting)

    section = extract_between_markers(
        main_text,
        [
            r"pick[-\s]*up\s*/\s*meeting\s*point",
            r"pickup\s*/\s*meeting\s*point",
            r"meeting\s*point\s*:",
            r"pick[-\s]*up\s*:",
        ],
        [
            r"\boverview\b",
            r"\bwhat'?s included\b",
            r"\bwhat’s included\b",
            r"\bwhat to expect\b",
            r"\bimportant info\b",
            r"\n\s*\n",
        ],
    )

    if section:
        return truncate_meeting_point_metadata(section)

    # Some long supplier descriptions use prose rather than a label, for example
    # "Meet our guide near the University of Oslo". Keep only the useful point.
    meet_match = re.search(
        r"meet\s+(?:our\s+)?(?:your\s+)?guide\s+(near|at)\s+([^.,\n]+)",
        main_text,
        flags=re.IGNORECASE,
    )
    if meet_match:
        prep = meet_match.group(1).lower()
        place = clean_space(meet_match.group(2))
        if prep == "near":
            return f"Near {place}"
        return place

    return ""


__all__ = ["extract_meeting_point_from_description", "truncate_meeting_point_metadata"]
