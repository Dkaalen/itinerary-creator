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


def get_important_travel_notes(output_edits=None):
    if output_edits and output_edits.get("important_travel_notes_text"):
        return text_to_list(output_edits.get("important_travel_notes_text"))
    return DEFAULT_IMPORTANT_TRAVEL_NOTES


__all__ = [
    "clean_activity_inclusion_items",
    "create_optional_addons",
    "get_fallback_activity_inclusions",
    "get_important_travel_notes",
    "prioritize_inline_inclusions",
    "render_optional_addons_pages",
]
