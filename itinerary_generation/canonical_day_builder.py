"""Canonical day builder."""

from __future__ import annotations

import re

from itinerary_generation.canonical_helpers import _row_id
from itinerary_generation.canonical_model import CanonicalDay
from itinerary_generation.content_engine import clean_client_title, sanitize_day_intro
from itinerary_generation.copy.visit_context import DayVisitContext
from itinerary_generation.day_content_resolver import resolve_day_content
from itinerary_generation.group_tour_rendering import group_tour_day_from_rows
from itinerary_generation.supplier_cleanup_brain import clean_supplier_title
from text_polish import polish_title


def canonical_day(
    day: str,
    rows: list[dict],
    *,
    output_edits: dict | None = None,
    detail_level: str = "Rich descriptive",
    visit_context: DayVisitContext | None = None,
) -> CanonicalDay:
    resolved = resolve_day_content(day, rows, output_edits=output_edits, detail_level=detail_level, visit_context=visit_context)
    group_tour_day = group_tour_day_from_rows(rows)
    raw_title = str(resolved.title or "").strip()
    if group_tour_day or " & " in raw_title or re.search(r"\b(?:and|Arrival in|Return to|Departure from|Next Stay)\b", raw_title):
        display_title = clean_supplier_title(raw_title)
    else:
        display_title = clean_client_title(raw_title, rows[0] if rows else {})
    if display_title:
        display_title = display_title[:1].upper() + display_title[1:]
    number = str(day).replace("Day", "").strip() or str(day).strip()
    return CanonicalDay(
        day=day,
        number=number,
        city=polish_title(resolved.city),
        title=display_title,
        intro=sanitize_day_intro(resolved.intro, rows),
        source_row_ids=[_row_id(row) for row in rows if _row_id(row)],
    )
