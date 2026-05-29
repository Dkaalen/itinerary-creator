import streamlit as st

from itinerary_generation.common import get_primary_city, get_row_type, group_rows_by_day
from itinerary_generation.day_text import create_day_intro
from itinerary_generation.titles import create_day_title
from itinerary_generation.cover_theme import SEASON_LABELS, SEASON_SUBTITLES, SEASON_TITLES, get_cover_season, get_cover_theme
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES
from ui.render_helpers import get_activity_description, list_to_text
from ui.output_edits import (
    apply_rich_writing_to_all_days,
    apply_rich_writing_to_day,
    make_output_edit_state,
    mark_output_dirty,
)
from app_modules.display_settings import get_detail_level_name
from app_modules.image_review import render_picture_studio


def render_output_editor(parsed_rows, grouped_days, output_edits):
    st.markdown('<div class="workflow-note">Edit the generated output here. The raw Excel input above is not changed.</div>', unsafe_allow_html=True)

    reset_col, help_col = st.columns([1, 3])
    with reset_col:
        if st.button("Reset edits", help="Return the editable fields to the generated text."):
            st.session_state.output_edits = make_output_edit_state(
                st.session_state.parsed_rows,
                group_rows_by_day(st.session_state.parsed_rows),
            )
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"
            st.rerun()
    with help_col:
        st.caption("Tip: edit only the fields you need. The preview and export files update from these fields automatically.")

    with st.expander("Built-in writing assistant", expanded=False):
        st.caption(
            "Use this to make the day-by-day text warmer and fuller. "
            "It is a local rule-based helper, not an external AI call, and all suggestions remain editable."
        )
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("Improve all day-to-day text", key="assistant_improve_all_days", use_container_width=True):
                st.session_state.output_edits = apply_rich_writing_to_all_days(
                    st.session_state.parsed_rows,
                    st.session_state.output_edits,
                )
                mark_output_dirty()
                st.rerun()
        with col_b:
            st.caption("Updates day intros and sparse activity descriptions using the rich client-facing style.")

    render_picture_studio(grouped_days, output_edits)

    with st.expander("Cover and summary pages", expanded=False):
        season_options = ["automatic", "winter", "spring", "summer", "autumn"]
        current_season = output_edits.get("cover_season", "automatic")
        if current_season not in season_options:
            current_season = "automatic"
        detected_season = get_cover_season(parsed_rows, {"cover_season": "automatic"})
        selected_cover_season = st.selectbox(
            "Cover season",
            season_options,
            index=season_options.index(current_season),
            format_func=lambda value: "Automatic" if value == "automatic" else SEASON_LABELS.get(value, value.title()),
            help=f"Automatic currently detects: {SEASON_LABELS.get(detected_season, detected_season.title())}.",
            key="edit_cover_season",
        )
        if selected_cover_season != current_season:
            current_title = output_edits.get("trip_title", "")
            current_subtitle = output_edits.get("trip_subtitle", "")
            output_edits["cover_season"] = selected_cover_season
            cover_theme = get_cover_theme(parsed_rows, output_edits)
            if not current_title or current_title in set(SEASON_TITLES.values()):
                output_edits["trip_title"] = cover_theme.get("title", current_title)
            if not current_subtitle or current_subtitle in set(SEASON_SUBTITLES.values()):
                output_edits["trip_subtitle"] = cover_theme.get("subtitle", current_subtitle)
        else:
            output_edits["cover_season"] = selected_cover_season
        output_edits["cover_kicker"] = st.text_input(
            "Cover label",
            value=output_edits.get("cover_kicker", "Travel Itinerary"),
            key="edit_cover_kicker",
        )
        output_edits["trip_title"] = st.text_input(
            "Cover title",
            value=output_edits.get("trip_title", ""),
            key="edit_trip_title",
        )
        output_edits["trip_subtitle"] = st.text_area(
            "Cover subtitle",
            value=output_edits.get("trip_subtitle", ""),
            height=80,
            key="edit_trip_subtitle",
        )
        output_edits["destinations_line"] = st.text_input(
            "Destinations line",
            value=output_edits.get("destinations_line", ""),
            key="edit_destinations_line",
        )

    days = list(grouped_days.keys())

    if days:
        day_tabs = st.tabs(days)

        for tab, day in zip(day_tabs, days):
            with tab:
                rows = grouped_days[day]
                day_edit = output_edits.setdefault("days", {}).setdefault(day, {})

                if st.button("Improve this day text", key=f"assistant_improve_{day}"):
                    st.session_state.output_edits = apply_rich_writing_to_day(
                        day,
                        rows,
                        st.session_state.output_edits,
                    )
                    mark_output_dirty()
                    st.rerun()

                day_edit["title"] = st.text_input(
                    f"{day} title",
                    value=day_edit.get("title", create_day_title(rows)),
                    key=f"edit_{day}_title",
                )
                day_edit["city"] = st.text_input(
                    f"{day} city",
                    value=day_edit.get("city", get_primary_city(rows)),
                    key=f"edit_{day}_city",
                )
                day_edit["intro"] = st.text_area(
                    f"{day} intro",
                    value=day_edit.get("intro", create_day_intro(rows, detail_level=get_detail_level_name(output_edits))),
                    height=95,
                    key=f"edit_{day}_intro",
                )

                with st.expander(f"Edit {day} itinerary items", expanded=False):
                    for index, row in enumerate(rows, start=1):
                        row_id = row.get("row_id") or f"{day}_{index}"
                        row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
                        row_type = get_row_type(row)
                        item_label = row_edit.get("title") or row.get("title") or f"Item {index}"

                        with st.expander(f"{index}. {row_type}: {item_label}", expanded=False):
                            row_edit["title"] = st.text_input(
                                "Title / text",
                                value=row_edit.get("title", row.get("title", "")),
                                key=f"edit_{row_id}_title",
                            )
                            row_edit["city"] = st.text_input(
                                "City / location",
                                value=row_edit.get("city", row.get("city", "")),
                                key=f"edit_{row_id}_city",
                            )

                            if row_type == "Hotel":
                                row_edit["hotel_name"] = st.text_input(
                                    "Accommodation name",
                                    value=row_edit.get("hotel_name", row.get("hotel_name", "")),
                                    key=f"edit_{row_id}_hotel_name",
                                )
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    row_edit["hotel_nights"] = st.text_input(
                                        "Number of nights",
                                        value=row_edit.get("hotel_nights", row.get("hotel_nights", "")),
                                        key=f"edit_{row_id}_hotel_nights",
                                    )
                                    row_edit["room_category"] = st.text_input(
                                        "Room category",
                                        value=row_edit.get("room_category", row.get("room_category", "")),
                                        key=f"edit_{row_id}_room",
                                    )
                                with col_b:
                                    row_edit["meal_plan"] = st.text_input(
                                        "Meal plan",
                                        value=row_edit.get("meal_plan", row.get("meal_plan", "")),
                                        key=f"edit_{row_id}_meal",
                                    )
                            else:
                                col1, col2 = st.columns(2)
                                with col1:
                                    row_edit["time"] = st.text_input(
                                        "Time",
                                        value=row_edit.get("time", row.get("time", "")),
                                        key=f"edit_{row_id}_time",
                                    )
                                    row_edit["meeting_point"] = st.text_input(
                                        "Meeting point",
                                        value=row_edit.get("meeting_point", row.get("meeting_point", "")),
                                        key=f"edit_{row_id}_meeting",
                                    )
                                    row_edit["duration"] = st.text_input(
                                        "Duration",
                                        value=row_edit.get("duration", row.get("duration", "")),
                                        key=f"edit_{row_id}_duration",
                                    )
                                with col2:
                                    row_edit["end_point"] = st.text_input(
                                        "End point",
                                        value=row_edit.get("end_point", row.get("end_point", "")),
                                        key=f"edit_{row_id}_end",
                                    )
                                    row_edit["luggage_included"] = st.text_input(
                                        "Luggage included",
                                        value=row_edit.get("luggage_included", row.get("luggage_included", "")),
                                        key=f"edit_{row_id}_luggage",
                                    )

                                row_edit["notable_sights_text"] = st.text_area(
                                    "Notable sights, one per line",
                                    value=row_edit.get("notable_sights_text", list_to_text(row.get("notable_sights", []))),
                                    height=90,
                                    key=f"edit_{row_id}_sights",
                                )
                                if row_type == "Activity":
                                    if st.button("Suggest richer description", key=f"assistant_desc_{row_id}"):
                                        suggestion = get_activity_description(row, "Rich descriptive")
                                        if suggestion:
                                            row_edit["client_description"] = suggestion
                                            mark_output_dirty()
                                            st.rerun()
                                row_edit["client_description"] = st.text_area(
                                    "Short description / note",
                                    value=row_edit.get("client_description", row.get("client_description") or get_activity_description(row, get_detail_level_name(output_edits))),
                                    height=75,
                                    key=f"edit_{row_id}_description",
                                )
                                row_edit["includes_text"] = st.text_area(
                                    "Inclusions, one per line",
                                    value=row_edit.get("includes_text", list_to_text(row.get("includes", []))),
                                    height=100,
                                    key=f"edit_{row_id}_includes",
                                )

    with st.expander("Edit final inclusion / exclusion pages", expanded=False):
        st.caption("Leave the included-services box empty to use the automatic categorized inclusion page. Add text only when you want to override it manually.")
        output_edits["whats_included_text"] = st.text_area(
            "Manual override for What’s included, one item per line",
            value=output_edits.get("whats_included_text", ""),
            height=220,
            key="edit_whats_included_text",
        )
        output_edits["whats_not_included_text"] = st.text_area(
            "What’s not included, one item per line",
            value=output_edits.get("whats_not_included_text", ""),
            height=180,
            key="edit_whats_not_included_text",
        )
        output_edits["important_travel_notes_text"] = st.text_area(
            "Important travel notes, one paragraph per line",
            value=output_edits.get("important_travel_notes_text", list_to_text(DEFAULT_IMPORTANT_TRAVEL_NOTES)),
            height=240,
            key="edit_important_travel_notes_text",
        )
