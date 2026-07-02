"""Editable output state helpers for the itinerary app."""

import copy
import uuid

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - lightweight test/runtime fallback
    class _SessionState(dict):
        def __getattr__(self, key):
            return self.get(key)

        def __setattr__(self, key, value):
            self[key] = value

    class _NoStreamlit:
        session_state = _SessionState()

    st = _NoStreamlit()

from itinerary_generation.common import get_primary_city, get_row_type, group_rows_by_day
from itinerary_generation.day_text import create_day_intro, create_travel_route_label
from itinerary_generation.copy.visit_context import build_day_visit_contexts
from itinerary_generation.generated_ownership import INTRO_GENERATOR_VERSION, day_source_signature
from itinerary_generation.inclusions import create_whats_included
from itinerary_generation.tone_presets import (
    DEFAULT_TONE_PRESET,
    apply_tone_to_intro,
    apply_tone_to_title,
    normalize_tone_preset,
    tone_preset as resolve_tone_preset,
)
from itinerary_generation.titles import (
    create_client_activity_title,
    create_day_title,
    create_destinations_line,
    create_trip_subtitle,
    create_trip_title,
)
from itinerary_generation.cover_theme import get_cover_season
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES, DETAIL_LEVELS
from normalizer_modules.times import normalize_activity_display_time_fields
from ui.render_helpers import get_activity_description, list_to_text, text_to_list
from ui.picture_workflow import PICTURES_ADDED_KEY


def refresh_generated_text_for_detail_level(parsed_rows, output_edits, old_detail, new_detail):
    """Refresh generated intros/descriptions when detail level changes.

    Manual edits are preserved. A field is only replaced if it still matches
    the old generated wording. This keeps the detail selector useful without
    unexpectedly wiping custom edits.
    """
    if not parsed_rows or not output_edits or old_detail == new_detail:
        return output_edits

    old_detail = old_detail if old_detail in DETAIL_LEVELS else "Standard client itinerary"
    new_detail = new_detail if new_detail in DETAIL_LEVELS else "Standard client itinerary"
    grouped_days = group_rows_by_day(parsed_rows)
    visit_contexts = build_day_visit_contexts(grouped_days)

    for day, rows in grouped_days.items():
        day_edit = output_edits.setdefault("days", {}).setdefault(day, {})
        old_intro = create_day_intro(rows, detail_level=old_detail, visit_context=visit_contexts.get(str(day)))
        new_intro = create_day_intro(rows, detail_level=new_detail, visit_context=visit_contexts.get(str(day)))
        current_intro = day_edit.get("intro", "")
        if not current_intro or current_intro == old_intro or day_edit.get("intro_manual_override") is False:
            day_edit["intro"] = new_intro
            day_edit["intro_generated_value"] = new_intro
            day_edit["intro_generator_version"] = INTRO_GENERATOR_VERSION
            day_edit["intro_source_signature"] = day_source_signature(rows)
            day_edit["intro_manual_override"] = False

        for row in rows:
            row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
            row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
            # Description generation is centralized in the content engine.
            # Preserve manual descriptions only; do not overwrite with generic
            # fallback text when changing detail level.
            row_edit.setdefault("client_description", row.get("client_description", ""))

    output_edits["detail_level"] = new_detail
    return output_edits


def mark_output_dirty():
    st.session_state.pdf_bytes = None
    st.session_state.pdf_signature = None
    st.session_state.export_pdf_bytes = None
    st.session_state.export_pdf_signature = None
    st.session_state.pdf_status = "Needs refresh"


def apply_rich_writing_to_day(day, rows, output_edits, *, visit_context=None):
    """Use the built-in writing assistant to make one day warmer and fuller.

    This is intentionally local/rule-based: no external AI, no API key, and no
    hidden cost. It updates only the editable generated fields, so the user can
    still change everything manually afterwards.
    """

    output_edits = output_edits or {}
    day_edit = output_edits.setdefault("days", {}).setdefault(day, {})
    intro = create_day_intro(rows, detail_level="Rich descriptive", visit_context=visit_context)
    day_edit["intro"] = intro
    day_edit["intro_generated_value"] = intro
    day_edit["intro_generator_version"] = INTRO_GENERATOR_VERSION
    day_edit["intro_source_signature"] = day_source_signature(rows)
    day_edit["intro_manual_override"] = False

    for row in rows:
        row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
        row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
        # Do not pre-freeze generated activity descriptions in edit state.
        # Final descriptions are selected by the central content engine at render
        # time so real supplier text can outrank generic fallbacks. Manual edits
        # are still preserved through apply_output_edits().
        if get_row_type(row) == "Activity" and "client_description" not in row_edit:
            row_edit["client_description"] = row.get("client_description", "")

    output_edits["detail_level"] = "Rich descriptive"
    return output_edits


def apply_rich_writing_to_all_days(parsed_rows, output_edits):
    output_edits = output_edits or {}
    grouped_days = group_rows_by_day(parsed_rows)
    visit_contexts = build_day_visit_contexts(grouped_days)
    for day, rows in grouped_days.items():
        output_edits = apply_rich_writing_to_day(day, rows, output_edits, visit_context=visit_contexts.get(str(day)))
    output_edits["detail_level"] = "Rich descriptive"
    return output_edits


def make_output_edit_state(parsed_rows, grouped_days, *, tone_preset=None):
    selected_tone = normalize_tone_preset(tone_preset or st.session_state.get("tone_preset", DEFAULT_TONE_PRESET))
    selected_tone_detail = resolve_tone_preset(selected_tone).detail_level
    edits = {
        "draft_id": uuid.uuid4().hex,
        "cover_kicker": "Travel Itinerary",
        "cover_season": "automatic",
        "detected_cover_season": get_cover_season(parsed_rows, {"cover_season": "automatic"}),
        "trip_title": create_trip_title(parsed_rows, grouped_days),
        "trip_subtitle": create_trip_subtitle(parsed_rows, grouped_days),
        "destinations_line": create_destinations_line(parsed_rows),
        "color_preset": st.session_state.get("color_preset", "Classic Agent"),
        "detail_level": selected_tone_detail,
        "tone_preset": selected_tone,
        "day_page_layout": st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT),
        # New projects start in stable text-editing mode. Pictures are added
        # only after the user explicitly enters picture-review mode.
        PICTURES_ADDED_KEY: False,
        "days": {},
        "rows": {},
        "whats_included_text": "",
        "whats_included_mode": "auto_categorized",
        # Keep exclusions dynamic unless the user manually edits them.
        # Initializing this from a generic default list freezes out itinerary-
        # specific self-arranged flights/transfers and optional items.
        "whats_not_included_text": "",
        "important_travel_notes_text": list_to_text(DEFAULT_IMPORTANT_TRAVEL_NOTES),
    }

    visit_contexts = build_day_visit_contexts(grouped_days)
    for day, rows in grouped_days.items():
        intro = apply_tone_to_intro(create_day_intro(rows, detail_level=edits["detail_level"], visit_context=visit_contexts.get(str(day))), selected_tone)
        edits["days"][day] = {
            "title": apply_tone_to_title(create_day_title(rows, visit_context=visit_contexts.get(str(day))), selected_tone),
            "intro": intro,
            "intro_generated_value": intro,
            "intro_generator_version": INTRO_GENERATOR_VERSION,
            "intro_source_signature": day_source_signature(rows),
            "intro_manual_override": False,
            "city": create_travel_route_label(rows) or get_primary_city(rows),
        }

        for row in rows:
            row_id = row.get("row_id") or f'line_{row.get("line_number", len(edits["rows"]))}'
            title = create_client_activity_title(row) if get_row_type(row) == "Activity" else row.get("title", "")
            title = apply_tone_to_title(title, selected_tone)

            edits["rows"][row_id] = {
                "title": title,
                "city": row.get("city", ""),
                "time": row.get("time", ""),
                "duration": row.get("duration", ""),
                "client_description": row.get("client_description", ""),
                "meeting_point": row.get("meeting_point", ""),
                "end_point": row.get("end_point", ""),
                "luggage_included": row.get("luggage_included", ""),
                "hotel_name": row.get("hotel_name", ""),
                "hotel_nights": row.get("hotel_nights", ""),
                "room_category": row.get("room_category", ""),
                "meal_plan": row.get("meal_plan", ""),
                "notable_sights_text": list_to_text(row.get("notable_sights", [])),
                "includes_text": list_to_text(row.get("includes", [])),
            }

    return edits


def apply_output_edits(parsed_rows, output_edits):
    edited_rows = copy.deepcopy(parsed_rows)
    row_edits = (output_edits or {}).get("rows", {})

    for row in edited_rows:
        row["original_title"] = row.get("original_title") or row.get("title", "")
        row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
        edits = row_edits.get(row_id, {})

        for key in [
            "title",
            "city",
            "time",
            "duration",
            "client_description",
            "meeting_point",
            "end_point",
            "luggage_included",
            "hotel_name",
            "hotel_nights",
            "room_category",
            "meal_plan",
        ]:
            if key in edits:
                row[key] = edits.get(key, "")

        if "notable_sights_text" in edits:
            row["notable_sights"] = text_to_list(edits.get("notable_sights_text", ""))

        if "includes_text" in edits:
            row["includes"] = text_to_list(edits.get("includes_text", ""))

    # Rebuild typed display fields after user edits. This intentionally leaves
    # the editable/source ``time`` value unchanged; renderers should consume
    # ``display_time`` when they need a client-facing range.
    for row in edited_rows:
        normalize_activity_display_time_fields(row)

    return edited_rows
