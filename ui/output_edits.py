"""Editable output state helpers for the itinerary app."""

import copy

import streamlit as st

from generator import (
    create_client_activity_title,
    create_day_intro,
    create_day_title,
    create_destinations_line,
    create_trip_subtitle,
    create_trip_title,
    create_whats_included,
    create_whats_not_included,
    get_primary_city,
    get_row_type,
    group_rows_by_day,
)
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES, DETAIL_LEVELS
from ui.day_rendering import display_time_with_duration, get_activity_description, list_to_text, text_to_list


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

    for day, rows in grouped_days.items():
        day_edit = output_edits.setdefault("days", {}).setdefault(day, {})
        old_intro = create_day_intro(rows, detail_level=old_detail)
        new_intro = create_day_intro(rows, detail_level=new_detail)
        current_intro = day_edit.get("intro", "")
        if not current_intro or current_intro == old_intro:
            day_edit["intro"] = new_intro

        for row in rows:
            row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
            row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
            old_description = get_activity_description(row, old_detail)
            new_description = get_activity_description(row, new_detail)
            current_description = row_edit.get("client_description", "")
            if old_description and (not current_description or current_description == old_description):
                row_edit["client_description"] = new_description

    output_edits["detail_level"] = new_detail
    return output_edits


def mark_output_dirty():
    st.session_state.pdf_bytes = None
    st.session_state.pdf_status = "Needs refresh"


def apply_rich_writing_to_day(day, rows, output_edits):
    """Use the built-in writing assistant to make one day warmer and fuller.

    This is intentionally local/rule-based: no external AI, no API key, and no
    hidden cost. It updates only the editable generated fields, so the user can
    still change everything manually afterwards.
    """

    output_edits = output_edits or {}
    day_edit = output_edits.setdefault("days", {}).setdefault(day, {})
    day_edit["intro"] = create_day_intro(rows, detail_level="Rich descriptive")

    for row in rows:
        row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
        row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
        if get_row_type(row) == "Activity":
            description = get_activity_description(row, "Rich descriptive")
            if description:
                row_edit["client_description"] = description

    output_edits["detail_level"] = "Rich descriptive"
    return output_edits


def apply_rich_writing_to_all_days(parsed_rows, output_edits):
    output_edits = output_edits or {}
    grouped_days = group_rows_by_day(parsed_rows)
    for day, rows in grouped_days.items():
        output_edits = apply_rich_writing_to_day(day, rows, output_edits)
    output_edits["detail_level"] = "Rich descriptive"
    return output_edits


def make_output_edit_state(parsed_rows, grouped_days):
    edits = {
        "cover_kicker": "Curated Travel Itinerary",
        "trip_title": create_trip_title(parsed_rows, grouped_days),
        "trip_subtitle": create_trip_subtitle(parsed_rows, grouped_days),
        "destinations_line": create_destinations_line(parsed_rows),
        "color_preset": st.session_state.get("color_preset", "Classic Agent"),
        "detail_level": "Rich descriptive",
        "day_page_layout": st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT),
        "days": {},
        "rows": {},
        "whats_included_text": "",
        "whats_included_mode": "auto_categorized",
        "whats_not_included_text": list_to_text(create_whats_not_included()),
        "important_travel_notes_text": list_to_text(DEFAULT_IMPORTANT_TRAVEL_NOTES),
    }

    for day, rows in grouped_days.items():
        edits["days"][day] = {
            "title": create_day_title(rows),
            "intro": create_day_intro(rows, detail_level=edits["detail_level"]),
            "city": get_primary_city(rows),
        }

        for row in rows:
            row_id = row.get("row_id") or f'line_{row.get("line_number", len(edits["rows"]))}'
            title = create_client_activity_title(row) if get_row_type(row) == "Activity" else row.get("title", "")

            edits["rows"][row_id] = {
                "title": title,
                "city": row.get("city", ""),
                "time": row.get("time", ""),
                "duration": row.get("duration", ""),
                "client_description": row.get("client_description") or get_activity_description(row, edits["detail_level"]),
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

    # Final display-level guardrail: even if Streamlit session edits contain an
    # old single start time, activities with a reliable duration should render as
    # a start-end range. This keeps preview and PDF export consistent after code
    # updates without requiring manual edit resets.
    for row in edited_rows:
        if get_row_type(row) == "Activity":
            row["time"] = display_time_with_duration(row.get("time", ""), row.get("duration", ""))

    return edited_rows
