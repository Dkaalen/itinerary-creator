"""Canonical day builder."""

from __future__ import annotations

from itinerary_generation.canonical_helpers import _row_id
from itinerary_generation.canonical_model import CanonicalDay
from itinerary_generation.common import get_primary_city, get_row_type
from itinerary_generation.content_engine import clean_client_title, is_group_tour_overview, sanitize_day_intro
from itinerary_generation.day_planner import plan_day
from itinerary_generation.day_text import create_day_intro
from itinerary_generation.titles import create_day_title
from text_polish import polish_title


def canonical_day(day: str, rows: list[dict], *, output_edits: dict | None = None, detail_level: str = "Rich descriptive") -> CanonicalDay:
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    plan = plan_day(rows)
    title = day_edits.get("title") or plan.title or create_day_title(rows)
    has_group_tour_overview = any(is_group_tour_overview(row) for row in rows)
    if day_edits.get("intro"):
        intro = day_edits.get("intro")
    elif has_group_tour_overview:
        intro = create_day_intro(rows, detail_level=detail_level)
    else:
        intro = plan.intro or create_day_intro(rows, detail_level=detail_level)
    city = day_edits.get("city") or get_primary_city(rows)
    if not city and any(get_row_type(row) == "Cruise" for row in rows):
        city = "Cruise"
    number = str(day).replace("Day", "").strip() or str(day).strip()
    return CanonicalDay(
        day=day,
        number=number,
        city=polish_title(city),
        title=clean_client_title(title, rows[0] if rows else {}),
        intro=sanitize_day_intro(intro, rows),
        source_row_ids=[_row_id(row) for row in rows if _row_id(row)],
    )
