"""Guided group-tour wording helpers for day intro text."""

from __future__ import annotations

import re

from itinerary_generation.common import get_row_type
from itinerary_generation.content_engine import group_tour_pickup_window_from_overview, is_group_tour_overview


def _is_group_tour_overview(row):
    return is_group_tour_overview(row)


def _format_group_tour_pickup_range(hour, minute, suffix):
    start = f"{hour}:{minute} {suffix}"
    try:
        end_minute = int(minute) + 30
        end_hour = int(hour) + (1 if end_minute >= 60 else 0)
        end_minute = end_minute % 60
        if suffix == "PM" and end_hour > 12:
            end_hour -= 12
        return f"between {start} and {end_hour}:{end_minute:02d} {suffix}"
    except Exception:
        return f"at {start}"


def _extract_group_tour_overview_start_time(day_rows):
    for row in day_rows:
        pickup = group_tour_pickup_window_from_overview(row)
        if pickup:
            return pickup
    return ""


def _is_group_tour_start_day(day_rows):
    return any(_is_group_tour_overview(row) for row in day_rows) and any(get_row_type(row) == "Activity" for row in day_rows)


def _natural_group_tour_focus(activity_title: str, source_text: str = "") -> str:
    title = str(activity_title or "the first included experience").strip()
    combined = f"{title} {source_text}"
    lower = combined.lower()
    if "borgarfjör" in lower or "borgarfjord" in lower:
        return "the Borgarfjörður region and its waterfalls"
    if "snæfellsnes" in lower or "snaefellsnes" in lower:
        return "the Snæfellsnes Peninsula"
    if "golden circle" in lower:
        return "the Golden Circle"
    if "south coast" in lower and "glacier" in lower:
        return "the South Coast waterfalls and glacier landscape"
    if "jökulsárlón" in lower or "jokulsarlon" in lower:
        return "Jökulsárlón Glacier Lagoon, Diamond Beach and the ice cave landscape"
    if "eastfjords" in lower:
        return "the Eastfjords and local life"
    if "north iceland" in lower or "mývatn" in lower or "myvatn" in lower:
        return "North Iceland"
    if "whale" in lower and "hauganes" in lower:
        return "Whale Watching in Hauganes before the return to Reykjavík"
    if "whale" in lower:
        return "Whale Watching"
    title = re.sub(r"^(Explore|Discover|Hike|Visit|Experience|Watch)\s+", "", title, flags=re.IGNORECASE).strip()
    if not title:
        return str(activity_title or "the first included experience")
    if re.search(r"[&]|Valley|Waterfalls|Circle|Coast|Lagoon|Peninsula|Fjord|Tour", title):
        return f"the {title}"
    return title[:1].lower() + title[1:]


