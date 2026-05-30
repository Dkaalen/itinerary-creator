"""Content-driven cover background selection.

The cover season is still the main visual direction, but certain strong
itinerary themes get a more specific background asset. Keep this logic here so
HTML, PDF and visual-editor previews use the same image choice.
"""

from __future__ import annotations

from itinerary_generation.common import get_row_type, main_rows_only


def _row_text(row: dict) -> str:
    parts = [
        row.get("type", ""),
        row.get("effective_type", ""),
        row.get("title", ""),
        row.get("original_title", ""),
        row.get("details", ""),
        row.get("city", ""),
    ]
    parts.extend(str(item) for item in row.get("includes", []) or [])
    return " ".join(str(part or "") for part in parts).lower()


def has_northern_lights_activity(parsed_rows) -> bool:
    """Return True when an itinerary includes a real aurora/Northern Lights experience."""

    markers = [
        "northern light",
        "northern lights",
        "aurora",
        "auroras",
        "aurora borealis",
    ]
    for row in main_rows_only(parsed_rows or []):
        row_type = get_row_type(row)
        if row_type == "Hotel":
            continue
        text = _row_text(row)
        if any(marker in text for marker in markers):
            return True
    return False


def count_rail_travel_rows(parsed_rows) -> int:
    """Count rail-heavy travel rows for context-driven cover selection.

    The input sometimes classifies scenic rail routes as Activity rows, so this
    deliberately looks at row content rather than row type alone.
    """

    rail_markers = [
        "train",
        "rail",
        "railway",
        "overnight train",
        "day train",
        "santa claus express",
        "flåm railway",
        "flam railway",
        "bergen railway",
        "norway in a nutshell",
    ]
    count = 0
    for row in main_rows_only(parsed_rows or []):
        if get_row_type(row) == "Hotel":
            continue
        text = _row_text(row)
        if any(marker in text for marker in rail_markers):
            count += 1
    return count


def select_cover_background_key(season: str, parsed_rows) -> str:
    """Return the asset key to use for the itinerary cover background."""

    season_key = str(season or "summer").strip().lower() or "summer"

    if season_key in {"winter", "autumn"} and has_northern_lights_activity(parsed_rows):
        return f"{season_key}_northern_lights"

    if season_key == "summer" and count_rail_travel_rows(parsed_rows) >= 2:
        return "summer-rail"

    return season_key
