"""Canonical accommodation block builder."""

from __future__ import annotations

import re

from itinerary_generation.canonical_helpers import _row_id, _source_text
from itinerary_generation.canonical_model import CanonicalBlock
from text_polish import polish_client_text
from itinerary_generation.accommodation_display_helpers import (
    is_self_arranged_accommodation,
    self_arranged_accommodation_label,
)
from itinerary_generation.accommodation_brain import accommodation_brain_for_row
from itinerary_generation.accommodation_inclusions import extract_stay_inclusions


def canonical_accommodation_block(row: dict) -> CanonicalBlock:
    if is_self_arranged_accommodation(row):
        return CanonicalBlock(
            kind="accommodation",
            row_id=_row_id(row),
            section_title="Accommodation",
            title=self_arranged_accommodation_label(row),
            lines=[],
            source_row_ids=[_row_id(row)],
        )

    brain = accommodation_brain_for_row(row)
    raw_room_category = str(row.get("room_category") or "")
    accommodation_line = brain.title
    if re.search(r"\bor\s+similar\b", _source_text(row), flags=re.IGNORECASE):
        if not re.search(r"\bor\s+similar\b", accommodation_line, flags=re.IGNORECASE):
            if re.search(r"\s+in\s+", accommodation_line, flags=re.IGNORECASE):
                accommodation_line = re.sub(r"\s+in\s+", " or similar in ", accommodation_line, count=1, flags=re.IGNORECASE)
            else:
                accommodation_line += " or similar"

    lines: list[str] = []
    if brain.room_line:
        line = brain.room_line
        # Room categories are source product names. Undo broad description-level
        # substitutions that are safe for prose but unsafe for room names.
        line = re.sub(r"\bNorthern Lights\s+Nest\b", "Aurora Nest", line, flags=re.IGNORECASE)
        if re.search(r"\bpremium\s+double\s+igloo\b", raw_room_category, flags=re.IGNORECASE):
            if not re.search(r"\bpremium\s+double\s+igloo\b", line, flags=re.IGNORECASE):
                line = re.sub(r"\bdouble\s+igloo\b", "Premium Double Igloo", line, flags=re.IGNORECASE)
        lines.append(line)

    stay_inclusions = [*extract_stay_inclusions(row), *(row.get("hotel_amenities") or [])]
    if stay_inclusions:
        lines.append("Included with this stay:")
        lines.extend(dict.fromkeys(stay_inclusions))

    return CanonicalBlock(
        kind="accommodation",
        row_id=_row_id(row),
        section_title="Overnight" if row.get("is_group_tour_accommodation") else "Accommodation",
        title=accommodation_line,
        lines=lines,
        source_row_ids=[_row_id(row)],
    )
