"""Final-page rendering helpers.

This module keeps the public import surface used by older tests/renderers while
delegating activity-inclusion cleanup and optional-add-on handling to focused
modules.
"""

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


def _note_tuple(notes) -> tuple[str, ...]:
    return tuple(" ".join(str(note or "").split()) for note in notes if str(note or "").strip())


def _is_refreshable_default_notes(value) -> bool:
    notes = _note_tuple(text_to_list(value or ""))
    return bool(notes and notes in {_note_tuple(DEFAULT_IMPORTANT_TRAVEL_NOTES), _note_tuple(_LEGACY_DEFAULT_IMPORTANT_TRAVEL_NOTES)})


def get_important_travel_notes(output_edits=None):
    if output_edits and output_edits.get("important_travel_notes_text"):
        saved_notes = output_edits.get("important_travel_notes_text")
        if not _is_refreshable_default_notes(saved_notes):
            return text_to_list(saved_notes)
    return DEFAULT_IMPORTANT_TRAVEL_NOTES


__all__ = [
    "clean_activity_inclusion_items",
    "create_optional_addons",
    "get_fallback_activity_inclusions",
    "get_important_travel_notes",
    "prioritize_inline_inclusions",
    "render_optional_addons_pages",
]
