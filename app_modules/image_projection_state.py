"""Project committed itinerary state into deterministic image-matching rows."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from app_modules.session_state_keys import OUTPUT_EDITS_KEY, PARSED_ROWS_KEY


def _day_overview_image_row(day: str, day_edit: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return a synthetic image-context row for committed day-level edits."""

    if not isinstance(day_edit, Mapping):
        return None
    title = str(day_edit.get("title", "") or "").strip()
    city = str(day_edit.get("city", "") or "").strip()
    intro = str(day_edit.get("intro", "") or "").strip()
    if not any((title, city, intro)):
        return None
    return {
        "day": day,
        "type": "Day Overview",
        "effective_type": "Day Overview",
        "city": city,
        "title": title,
        "client_description": intro,
        "display_description": intro,
        "image_context_source": "committed_day_edit",
    }


def image_grouped_days_from_state(state: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return committed image-relevant rows grouped by day without mutating state."""

    from itinerary_generation.common import group_rows_by_day, is_optional_row
    from ui.output_edits import apply_output_edits

    parsed_rows = state.get(PARSED_ROWS_KEY, []) or []
    output_edits = state.get(OUTPUT_EDITS_KEY, {}) or {}
    edited_rows = apply_output_edits(parsed_rows, output_edits) if output_edits else deepcopy(parsed_rows)
    grouped_days = group_rows_by_day(edited_rows)
    day_edits = output_edits.get("days", {}) if isinstance(output_edits, Mapping) else {}

    image_grouped_days: dict[str, list[dict[str, Any]]] = {}
    for day, rows in grouped_days.items():
        usable_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
        day_edit = day_edits.get(day, {}) if isinstance(day_edits, Mapping) else {}
        overview_row = _day_overview_image_row(str(day), day_edit)
        image_grouped_days[day] = ([overview_row] if overview_row else []) + usable_rows
    return image_grouped_days


__all__ = ["image_grouped_days_from_state"]
