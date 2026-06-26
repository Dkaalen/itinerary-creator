"""Final-page rendering helpers.

This module keeps the public import surface used by older tests/renderers while
delegating activity-inclusion cleanup and optional-add-on handling to focused
modules.
"""

import re

from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES
from ui.render_helpers import text_to_list
from ui.activity_inclusions import (
    clean_activity_inclusion_items,
    get_fallback_activity_inclusions,
    prioritize_inline_inclusions,
)
from ui.optional_addons import create_optional_addons, render_optional_addons_pages

_LEGACY_DEFAULT_IMPORTANT_TRAVEL_NOTES = [
    "Transport schedules, including flights, trains, buses, ferries and cruises, are subject to operational changes. Final confirmed timings will be provided in the travel vouchers.",
    "Activities may be weather dependent and can be adjusted if required for safety, availability or operational reasons.",
    "Northern Lights sightings are a natural phenomenon and cannot be guaranteed. Tours are arranged to give the best possible opportunity based on local conditions.",
    "Hotel check-in and check-out times vary by property. As a general guideline, check-in in the Nordic region is usually between 3:00 PM and 4:30 PM, while check-out is usually between 10:00 AM and 12:00 noon.",
    "Route, road and rail conditions in the Nordic region can vary in winter. Please follow local guidance and allow extra time for independent transfers.",
]


def _rows_text(parsed_rows) -> str:
    return " ".join(
        " ".join(str(row.get(key) or "") for key in ("city", "title", "original_title", "details", "description"))
        for row in (parsed_rows or [])
    ).casefold()


def _rows_months(parsed_rows) -> set[int]:
    months: set[int] = set()
    for row in parsed_rows or []:
        for key in ("date", "start_date", "end_date"):
            value = str(row.get(key) or "")
            match = re.search(r"\b\d{1,2}[./-](\d{1,2})[./-]\d{2,4}\b", value)
            if match:
                try:
                    months.add(int(match.group(1)))
                except ValueError:
                    pass
    return months


def _contextual_default_notes(parsed_rows=None) -> list[str]:
    if parsed_rows is None:
        return list(DEFAULT_IMPORTANT_TRAVEL_NOTES)
    text = _rows_text(parsed_rows)
    months = _rows_months(parsed_rows)
    winter_months = {12, 1, 2, 3}
    has_northern_lights = any(marker in text for marker in ("northern lights", "aurora", "borealis"))
    has_winter_context = bool(months & winter_months) or any(marker in text for marker in ("winter", "snow", "arctic", "northern lights", "aurora"))

    notes: list[str] = []
    for note in DEFAULT_IMPORTANT_TRAVEL_NOTES:
        lower = note.casefold()
        if "northern lights" in lower and not has_northern_lights:
            continue
        is_independent_transfer_note = lower.startswith("some transfers are self-arranged")
        if ("winter" in lower or "snow" in lower or "arctic" in lower) and not has_winter_context and not is_independent_transfer_note:
            continue
        if is_independent_transfer_note and not has_winter_context:
            note = "Some transfers are self-arranged unless specifically listed as included. Please allow enough time between hotels, stations, airports and meeting points."
        notes.append(note)
    return notes


def _note_tuple(notes) -> tuple[str, ...]:
    return tuple(" ".join(str(note or "").split()) for note in notes if str(note or "").strip())


def _is_refreshable_default_notes(value) -> bool:
    notes = _note_tuple(text_to_list(value or ""))
    return bool(notes and notes in {_note_tuple(DEFAULT_IMPORTANT_TRAVEL_NOTES), _note_tuple(_LEGACY_DEFAULT_IMPORTANT_TRAVEL_NOTES)})


def get_important_travel_notes(output_edits=None, *, parsed_rows=None):
    if output_edits and output_edits.get("important_travel_notes_text"):
        saved_notes = output_edits.get("important_travel_notes_text")
        if not _is_refreshable_default_notes(saved_notes):
            return text_to_list(saved_notes)
    return _contextual_default_notes(parsed_rows)


__all__ = [
    "clean_activity_inclusion_items",
    "create_optional_addons",
    "get_fallback_activity_inclusions",
    "get_important_travel_notes",
    "prioritize_inline_inclusions",
    "render_optional_addons_pages",
]
