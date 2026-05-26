from pathlib import Path
import copy
import html
import json
import re

import streamlit as st
import diagnostics
from itinerary_parser import parse_itinerary, normalize_time_text
from normalizer import normalize_itinerary_rows
from pdf_exporter import export_html_to_pdf
from text_polish import (
    polish_client_text,
    polish_hotel_name,
    polish_inclusion_items,
    polish_inclusion_item,
    polish_title,
    expand_time_with_duration,
    format_duration_display,
)
from generator import (
    TRANSPORT_TYPES,
    create_client_activity_title,
    create_day_intro,
    create_day_title,
    create_destinations_line,
    create_journey_arc,
    create_trip_glance,
    create_trip_subtitle,
    create_trip_title,
    create_whats_included,
    create_whats_not_included,
    clean_include_item,
    get_primary_city,
    get_row_type,
    group_rows_by_day,
    is_route_transfer,
    get_transfer_travel_title,
    is_self_arranged,
)
from image_matcher import select_day_image, select_day_images, scan_image_bank, format_match_for_debug
from layout_policy import (
    DEFAULT_DAY_PAGE_LAYOUT,
    DAY_PAGE_LAYOUTS,
    normalize_day_page_layout,
    is_day_packing_enabled,
    is_three_day_packing_enabled as policy_is_three_day_packing_enabled,
)
from ui.app_constants import (
    COLOR_PRESETS,
    DEFAULT_IMPORTANT_TRAVEL_NOTES,
    DETAIL_LEVELS,
    PRESET_ORDER,
)
from ui.styles import apply_global_styles
from ui.day_rendering import (
    build_day_blocks,
    can_pack_days,
    can_pack_three_days,
    create_activity_inclusions,
    create_optional_addons,
    display_time,
    esc,
    get_activity_description,
    get_activity_logistics,
    get_day_pack_stats,
    get_important_travel_notes,
    is_self_arranged_transport,
    list_to_text,
    normalize_list,
    render_activity_inclusions_pages,
    render_day_pages,
    render_list_items,
    render_optional_addons_pages,
    render_split_list_pages,
    render_text_paragraph_page,
    text_to_list,
)
from ui.diagnostics_panel import render_parser_diagnostics_panel
from ui.export_files import build_full_html_document, save_html_file, save_pdf_file
from ui.output_edits import (
    apply_output_edits,
    apply_rich_writing_to_all_days,
    apply_rich_writing_to_day,
    make_output_edit_state,
    mark_output_dirty,
    refresh_generated_text_for_detail_level,
)
from visual_editor_component.editor_workflow import render_visual_editor
from images.app_image_selection import (
    CROP_FOCUS_LABELS,
    CROP_FOCUS_OPTIONS,
    CROP_FOCUS_OBJECT_POSITIONS,
    day_image_match_from_path,
    get_day_image_choice,
    get_day_image_crop_focus,
    get_day_image_overrides,
    get_image_bank_path,
    image_to_data_uri,
    infer_country_for_city,
    list_city_image_options,
    normalize_crop_focus,
    normalize_path_key,
    render_day_image_slot,
    save_uploaded_day_image,
    select_day_images_with_overrides,
    slugify_filename,
)


APP_VERSION = "2026-05-26 v36c19-visual-editor-split"


st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide",
)

apply_global_styles()




# Day-page layout options are centralized in layout_policy.py.



















def parse_and_normalize_itinerary(raw_text):
    """Parse raw input and always run the post-parser normalizer.

    The normalizer is where row-level client-facing fixes are finalized. This
    includes the requested rule: single start time + duration becomes a visible
    start-end range in the day-by-day itinerary.
    """
    return normalize_itinerary_rows(parse_itinerary(raw_text))



















def get_color_preset_name(output_edits=None):
    name = (output_edits or {}).get("color_preset") or st.session_state.get("color_preset", "Classic Agent")
    if name not in COLOR_PRESETS:
        return "Classic Agent"
    return name


def get_color_preset(output_edits=None):
    return COLOR_PRESETS[get_color_preset_name(output_edits)]


def get_detail_level_name(output_edits=None):
    """Return a safe client-facing detail level for the current state.

    This helper is intentionally defensive because the app can be rebuilt from
    session state, loaded project JSON, or freshly generated edits. A missing
    detail level should never break itinerary rendering.
    """
    return "Rich descriptive"




def get_day_page_layout_name(output_edits=None):
    name = (output_edits or {}).get("day_page_layout") or st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    return normalize_day_page_layout(name)


def is_smart_day_packing_enabled(output_edits=None):
    return is_day_packing_enabled(get_day_page_layout_name(output_edits))


def is_three_day_packing_enabled(output_edits=None):
    return policy_is_three_day_packing_enabled(get_day_page_layout_name(output_edits))























































































def get_duplicate_count(raw_text_value, parsed_rows=None):
    raw_rows = [
        line for line in raw_text_value.splitlines()
        if "day " in line.strip().lower()
    ]

    parsed_count = len(parsed_rows) if parsed_rows is not None else len(parse_itinerary(raw_text_value))

    return max(len(raw_rows) - parsed_count, 0)


def get_overflow_warnings(grouped_days):
    warnings = []

    for day, rows in grouped_days.items():
        activity_count = sum(1 for row in rows if get_row_type(row) == "Activity")
        block_count = len(rows)
        long_text_score = sum(len(str(row.get("title", ""))) for row in rows)

        if block_count >= 7 or activity_count >= 3 or long_text_score > 520:
            warnings.append(f"{day} may be too full for one A4 page. Review the editable output before exporting.")

    return warnings


def get_current_day_image_matches(output_edits):
    parsed_rows = st.session_state.get("parsed_rows", [])
    if not parsed_rows:
        return {}
    edited_rows = apply_output_edits(parsed_rows, output_edits)
    return select_day_images_with_overrides(group_rows_by_day(edited_rows), output_edits)


def set_day_image_mode(output_edits, day, mode, path=""):
    choice = get_day_image_choice(output_edits, day)
    choice["mode"] = mode
    choice["path"] = path if mode == "manual" else ""
    mark_output_dirty()


def render_day_picture_action_panel(day, rows, output_edits, current_match=None, key_prefix="picture_studio"):
    """Visible per-day picture controls used by the Picture Studio."""

    choice = get_day_image_choice(output_edits, day)
    city = get_primary_city(rows)
    current_path = Path(current_match.get("path")) if current_match else None

    st.markdown(f"#### {day} picture")
    if current_path and current_path.exists():
        st.image(str(current_path), caption=f"Current picture: {current_path.name}", use_container_width=True)
        if current_match and current_match.get("reason"):
            st.caption(f"Match: {current_match.get('reason')}")
    else:
        st.info("No picture is selected for this day. The PDF will leave this day without an image.")

    st.caption("Use these controls before creating the PDF. The PDF remains the source of truth for final image placement.")

    action_col_1, action_col_2, action_col_3 = st.columns(3)
    with action_col_1:
        if st.button("Use automatic", key=f"{key_prefix}_auto_{day}", use_container_width=True):
            set_day_image_mode(output_edits, day, "auto")
            st.rerun()
    with action_col_2:
        if st.button("Remove picture", key=f"{key_prefix}_remove_{day}", use_container_width=True):
            set_day_image_mode(output_edits, day, "none")
            st.rerun()
    with action_col_3:
        st.caption(f"Current mode: {choice.get('mode', 'auto')}")

    focus_value = normalize_crop_focus(choice.get("crop_focus", "top"))
    focus_label = CROP_FOCUS_LABELS.get(focus_value, "Sky / upper focus")
    new_focus_label = st.selectbox(
        "Re-crop focus",
        list(CROP_FOCUS_OPTIONS.keys()),
        index=list(CROP_FOCUS_OPTIONS.keys()).index(focus_label),
        key=f"{key_prefix}_crop_focus_{day}",
        help="Sky / upper focus is best for northern lights, skylines, mountains and wide landscapes.",
    )
    new_focus = CROP_FOCUS_OPTIONS[new_focus_label]
    if choice.get("crop_focus") != new_focus:
        choice["crop_focus"] = new_focus
        mark_output_dirty()

    options = list_city_image_options(city)
    st.markdown("**Replace from image bank**")
    if options:
        option_labels = [path.name for path in options]
        current_path_text = choice.get("path", "") if choice.get("mode") == "manual" else (str(current_path) if current_path else "")
        current_index = 0
        for idx, path in enumerate(options):
            if normalize_path_key(path) == normalize_path_key(current_path_text):
                current_index = idx
                break
        selected_name = st.selectbox(
            "Choose a picture",
            option_labels,
            index=current_index,
            key=f"{key_prefix}_replace_select_{day}",
        )
        selected_path = str(options[option_labels.index(selected_name)])
        if st.button("Replace with selected picture", key=f"{key_prefix}_replace_button_{day}", use_container_width=True):
            set_day_image_mode(output_edits, day, "manual", selected_path)
            st.rerun()
    else:
        st.warning(f"No image-bank pictures found for {city or 'this destination'}.")

    st.markdown("**Add a new picture**")
    add_col_1, add_col_2 = st.columns([1, 1])
    with add_col_1:
        upload_season = st.selectbox("Season", ["Summer", "Winter"], key=f"{key_prefix}_upload_season_{day}")
    with add_col_2:
        upload_label = st.text_input(
            "Picture label",
            value="",
            placeholder="Opera House, Northern Lights...",
            key=f"{key_prefix}_upload_label_{day}",
        )
    uploaded = st.file_uploader(
        "Upload JPG/PNG/WebP",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"{key_prefix}_upload_file_{day}",
    )
    if uploaded and st.button("Add and use uploaded picture", key=f"{key_prefix}_upload_use_{day}", use_container_width=True):
        saved_path = save_uploaded_day_image(uploaded, city, upload_season, upload_label)
        if saved_path:
            set_day_image_mode(output_edits, day, "manual", saved_path)
            st.success(f"Added {Path(saved_path).name} and selected it for {day}.")
            st.rerun()


def render_picture_studio(grouped_days, output_edits):
    """Make day-picture review obvious before PDF export."""

    days = list(grouped_days.keys())
    if not days:
        return

    if st.session_state.get("active_image_day") not in days:
        st.session_state.active_image_day = days[0]

    image_matches = get_current_day_image_matches(output_edits)

    with st.expander("Picture review & controls", expanded=True):
        st.caption(
            "Review the pictures before PDF export. Select a day, then remove, replace, upload, or adjust the crop focus. "
            "The final PDF uses the premium full-width, bottom-edge layout."
        )

        card_columns = st.columns(min(3, max(1, len(days))))
        for index, day in enumerate(days):
            rows = grouped_days[day]
            match = image_matches.get(day)
            current_path = Path(match.get("path")) if match else None
            with card_columns[index % len(card_columns)]:
                st.markdown(f"**{day}**")
                if current_path and current_path.exists():
                    st.image(str(current_path), caption=current_path.name, use_container_width=True)
                else:
                    st.info("No picture")
                if st.button("Edit picture", key=f"picture_studio_open_{day}", use_container_width=True):
                    st.session_state.active_image_day = day
                    st.rerun()

        active_day = st.session_state.get("active_image_day", days[0])
        st.divider()
        render_day_picture_action_panel(
            active_day,
            grouped_days[active_day],
            output_edits,
            current_match=image_matches.get(active_day),
            key_prefix="picture_studio_active",
        )

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
        output_edits["whats_included_text"] = st.text_area(
            "What’s included, one item per line",
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


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    output_edits = output_edits or {}
    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)
    colors_json = esc(json.dumps(colors))

    trip_title = output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    trip_subtitle = output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    destinations_line = output_edits.get("destinations_line") or create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    journey_arc = create_journey_arc(grouped_days)

    if output_edits.get("whats_included_text"):
        whats_included = text_to_list(output_edits.get("whats_included_text"))
    else:
        whats_included = create_whats_included(parsed_rows, grouped_days)

    optional_addons = create_optional_addons(parsed_rows)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included()

    important_travel_notes = get_important_travel_notes(output_edits)

    html_text = f"""
    <style>
        .preview-background {{
            --page-bg: {esc(colors['page_bg'])};
            --preview-bg: {esc(colors['preview_bg'])};
            --ink: {esc(colors['ink'])};
            --body: {esc(colors['body'])};
            --muted: {esc(colors['muted'])};
            --line: {esc(colors['line'])};
            --card: {esc(colors['card'])};
            --accent: {esc(colors['accent'])};
            background: var(--preview-bg);
            padding: 32px 0 60px 0;
        }}

        .a4-page {{
            width: 794px;
            min-height: 1123px;
            background: var(--page-bg);
            color: var(--ink);
            margin: 0 auto 32px auto;
            padding: 66px 64px;
            box-sizing: border-box;
            font-family: Georgia, 'Times New Roman', serif;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
            break-after: page;
            page-break-after: always;
            overflow: hidden;
        }}

        .cover-page {{
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        .single-day-page {{
            display: flex;
            flex-direction: column;
        }}

        .single-day-page .day-section {{
            flex: 0 0 auto;
        }}

        .day-image-slot {{
            margin: auto -64px -66px -64px;
            height: 410px;
            overflow: hidden;
            flex: 0 0 410px;
        }}

        .day-image-preview-img {{
            display: block;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 25%;
        }}

        .cover-kicker {{
            font-family: Arial, sans-serif;
            font-size: 13px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 18px;
        }}

        .cover-title {{
            font-size: 54px;
            line-height: 1.05;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 18px;
        }}

        .cover-subtitle {{
            font-size: 24px;
            line-height: 1.25;
            color: var(--ink);
            margin-bottom: 18px;
        }}

        .cover-destinations {{
            font-family: Arial, sans-serif;
            font-size: 15px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--body);
            margin-top: 24px;
        }}

        .glance-card,
        .journey-arc {{
            background: var(--card);
            border: 1px solid var(--line);
            padding: 28px;
        }}

        .glance-card {{
            margin-bottom: 34px;
        }}

        .glance-title,
        .journey-title {{
            font-size: 30px;
            margin-bottom: 16px;
            color: var(--ink);
        }}

        .glance-row {{
            display: grid;
            grid-template-columns: 165px 1fr;
            gap: 18px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            padding: 8px 0;
            border-bottom: 1px solid var(--line);
        }}

        .glance-label {{
            font-weight: 700;
            color: var(--ink);
        }}

        .glance-value {{
            color: var(--body);
        }}

        .journey-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: var(--body);
        }}

        .journey-table th {{
            text-align: left;
            color: var(--ink);
            font-weight: 700;
            padding: 10px 8px;
            border-bottom: 1px solid var(--line);
        }}

        .journey-table td {{
            padding: 12px 8px;
            vertical-align: top;
            border-bottom: 1px solid var(--line);
            line-height: 1.45;
        }}

        .journey-days {{
            white-space: nowrap;
        }}

        .day-label {{
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 6px;
            color: var(--ink);
        }}

        .day-title {{
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 12px;
            color: var(--ink);
        }}

        .city {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 20px;
        }}

        .intro {{
            font-size: 15px;
            line-height: 1.5;
            margin-bottom: 22px;
            color: var(--body);
        }}

        .content-block {{
            margin-bottom: 15px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .packed-day-page {{
            padding-top: 46px;
            padding-bottom: 46px;
        }}

        .packed-section .day-label {{
            font-size: 34px;
            margin-bottom: 4px;
        }}

        .packed-section .day-title {{
            font-size: 27px;
            line-height: 1.16;
            margin-bottom: 8px;
        }}

        .packed-section .city {{
            font-size: 12px;
            margin-bottom: 10px;
        }}

        .packed-section .intro {{
            font-size: 15px;
            line-height: 1.42;
            margin-bottom: 12px;
        }}

        .packed-section .content-block {{
            margin-bottom: 8px;
        }}

        .packed-section .section-title {{
            font-size: 11px;
            margin-top: 9px;
            margin-bottom: 3px;
        }}

        .packed-section .body-text,
        .packed-section li {{
            font-size: 13.5px;
            line-height: 1.32;
            margin-bottom: 2px;
        }}

        .packed-section ul {{
            margin-top: 3px;
            margin-bottom: 6px;
            padding-left: 17px;
        }}

        .day-separator {{
            height: 1px;
            background: var(--line);
            margin: 16px 0 13px 0;
        }}

        .triple-day-page {{
            padding-top: 38px;
            padding-bottom: 38px;
        }}

        .triple-day-page .day-separator {{
            margin: 9px 0 8px 0;
        }}

        .triple-packed-section .day-label {{
            font-size: 34px;
            margin-bottom: 3px;
        }}

        .triple-packed-section .day-title {{
            font-size: 27px;
            line-height: 1.16;
            margin-bottom: 7px;
        }}

        .triple-packed-section .city {{
            font-size: 12px;
            margin-bottom: 8px;
        }}

        .triple-packed-section .intro {{
            font-size: 15px;
            line-height: 1.38;
            margin-bottom: 9px;
        }}

        .triple-packed-section .content-block {{
            margin-bottom: 5px;
        }}

        .triple-packed-section .section-title {{
            font-size: 11px;
            margin-top: 7px;
            margin-bottom: 2px;
        }}

        .triple-packed-section .body-text,
        .triple-packed-section li {{
            font-size: 13.5px;
            line-height: 1.30;
            margin-bottom: 1px;
        }}

        .triple-packed-section ul {{
            margin-top: 2px;
            margin-bottom: 4px;
            padding-left: 15px;
        }}

        .section-title {{
            font-family: Arial, sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-top: 15px;
            margin-bottom: 5px;
            color: var(--accent);
        }}

        .small-section {{
            margin-top: 10px;
        }}

        .body-text {{
            font-size: 13.5px;
            line-height: 1.38;
            color: var(--body);
            margin-bottom: 5px;
        }}

        .strong-line {{
            font-weight: 600;
        }}

        .meta-label {{
            font-family: Arial, sans-serif;
            font-weight: 700;
            font-size: 12px;
            color: var(--ink);
        }}

        .final-page-title {{
            font-size: 34px;
            margin-bottom: 22px;
            color: var(--ink);
        }}

        .activity-inclusion-block {{
            margin-bottom: 18px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .activity-inclusion-title {{
            font-size: 18px;
            line-height: 1.25;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 6px;
        }}

        ul {{
            margin-top: 5px;
            margin-bottom: 13px;
            padding-left: 21px;
        }}

        li {{
            font-size: 13.5px;
            line-height: 1.36;
            margin-bottom: 3px;
            color: var(--body);
        }}

        .final-list li {{
            margin-bottom: 5px;
        }}

        .important-notes-page .note-paragraph {{
            font-size: 14px;
            line-height: 1.55;
            margin-bottom: 14px;
        }}

        .notes-block {{
            margin-top: 8px;
        }}

        @media print {{
            @page {{
                size: A4 portrait;
                margin: 0;
            }}

            .preview-background {{
                background: white;
                padding: 0;
            }}

            .a4-page {{
                width: 210mm;
                height: 297mm;
                min-height: 297mm;
                margin: 0;
                box-shadow: none;
                break-after: page;
                page-break-after: always;
            }}
        }}
    </style>

    <div class="preview-background" data-preset="{esc(preset_name)}" data-colors="{colors_json}">

        <div class="a4-page cover-page">
            <div class="cover-kicker">Curated Travel Itinerary</div>
            <div class="cover-title">{esc(trip_title)}</div>
            <div class="cover-subtitle">{esc(trip_subtitle)}</div>
            <div class="cover-destinations">{esc(destinations_line)}</div>
        </div>

        <div class="a4-page">
            <div class="glance-card">
                <div class="glance-title">Your Trip at a Glance</div>
    """

    for label, value in trip_glance.items():
        html_text += f"""
                <div class="glance-row">
                    <div class="glance-label">{esc(label)}</div>
                    <div class="glance-value">{esc(value)}</div>
                </div>
        """

    html_text += """
            </div>

            <div class="journey-arc">
                <div class="journey-title">Your Journey Arc</div>
                <table class="journey-table">
                    <thead>
                        <tr>
                            <th>Chapter</th>
                            <th>Days</th>
                            <th>What You’ll Experience</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for chapter in journey_arc:
        html_text += f"""
                        <tr>
                            <td>{esc(chapter["chapter"])}</td>
                            <td class="journey-days">{esc(chapter["days"])}</td>
                            <td>{esc(chapter["experience"])}</td>
                        </tr>
        """

    html_text += """
                    </tbody>
                </table>
            </div>
        </div>
    """

    html_text += render_day_pages(grouped_days, output_edits)

    html_text += render_split_list_pages("What’s included", whats_included)
    html_text += render_optional_addons_pages(optional_addons)
    html_text += render_split_list_pages("What’s not included", whats_not_included)
    html_text += render_text_paragraph_page("Important travel notes", important_travel_notes)

    html_text += "</div>"

    return html_text















def get_current_itinerary_state():
    """Return edited rows/grouped days for the current session state."""
    parsed_rows = st.session_state.get("parsed_rows", [])
    output_edits = st.session_state.get("output_edits", {})

    if not parsed_rows:
        return [], {}

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    return edited_rows, group_rows_by_day(edited_rows)


def get_itinerary_stats(parsed_rows=None, grouped_days=None):
    parsed_rows = parsed_rows if parsed_rows is not None else st.session_state.get("parsed_rows", [])
    grouped_days = grouped_days if grouped_days is not None else group_rows_by_day(parsed_rows)

    destinations = []
    for row in parsed_rows:
        city = str(row.get("city", "")).strip()
        if city and city not in destinations:
            destinations.append(city)

    activities = [row for row in parsed_rows if get_row_type(row) == "Activity" and not row.get("is_optional")]
    optional_rows = [row for row in parsed_rows if row.get("is_optional")]
    hotels = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    self_arranged = [row for row in parsed_rows if is_self_arranged_transport(row)]

    return {
        "days": len(grouped_days),
        "destinations": len(destinations),
        "destination_names": destinations,
        "activities": len(activities),
        "hotels": len(hotels),
        "self_arranged": len(self_arranged),
        "optional_rows": len(optional_rows),
    }




def make_title_suggestions(parsed_rows, grouped_days):
    cities = []
    for row in parsed_rows:
        city = str(row.get("city", "")).strip()
        if city and city not in cities:
            cities.append(city)

    full_text = " ".join(str(row.get("details", "")) for row in parsed_rows).lower()
    suggestions = []

    if any(marker in full_text for marker in ["northern light", "aurora", "lapland", "arctic"]):
        suggestions.extend(["Nordic Winter Journey", "Arctic Lights Journey", "Lapland & Nordic Lights Escape"])

    if "fjord" in full_text or "norway in a nutshell" in full_text:
        suggestions.extend(["Nordic Fjord Journey", "Fjords & Capitals Discovery", "Scenic Nordic Journey"])

    if len(cities) >= 4:
        suggestions.append("Grand Nordic Journey")

    if len(cities) == 2:
        suggestions.append(f"{cities[0]} & {cities[1]} Journey")

    if not suggestions:
        suggestions.extend(["Nordic Discovery Journey", "Curated Nordic Escape", "Scandinavian City & Nature Journey"])

    clean = []
    for suggestion in suggestions:
        if suggestion not in clean:
            clean.append(suggestion)
    return clean[:6]


def get_activity_sections_count(parsed_rows):
    return len(create_activity_inclusions(parsed_rows))


def build_review_items(parsed_rows=None, grouped_days=None):
    """Return practical client-facing review items for the sidebar.

    These are not technical parser diagnostics. They are consultant-friendly
    checks that help decide whether an itinerary should be reviewed before export.
    """

    parsed_rows = parsed_rows if parsed_rows is not None else st.session_state.get("parsed_rows", [])
    grouped_days = grouped_days if grouped_days is not None else group_rows_by_day(parsed_rows)
    items = []

    def add_item(severity, message):
        entry = {"severity": severity, "message": message}
        if entry not in items:
            items.append(entry)

    activities = [row for row in parsed_rows if get_row_type(row) == "Activity" and not row.get("is_optional")]
    hotels = [row for row in parsed_rows if get_row_type(row) == "Hotel" and not row.get("is_optional")]
    optional_rows = [row for row in parsed_rows if row.get("is_optional")]
    self_arranged = [row for row in parsed_rows if get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row) and not row.get("is_optional")]

    for row in activities:
        title = create_client_activity_title(row) or row.get("title", "Activity")
        text = f'{title} {row.get("details", "")}'.lower()
        day = row.get("day", "")
        meeting_label, meeting_point = get_activity_logistics(row)

        is_simple_ticket = any(marker in text for marker in ["hop-on", "hop on", "ticket", "fløibanen", "floibanen", "fjellheisen"])
        if not meeting_point and not is_simple_ticket:
            add_item("warning", f"{day}: activity may need a meeting point — {title}")
        if not row.get("duration") and not is_simple_ticket:
            add_item("info", f"{day}: activity has no duration — {title}")

    for row in hotels:
        day = row.get("day", "")
        name = row.get("hotel_name") or row.get("title") or "Accommodation"
        if not row.get("hotel_nights"):
            add_item("warning", f"{day}: accommodation missing number of nights — {name}")
        if not row.get("room_category"):
            add_item("info", f"{day}: accommodation missing room category — {name}")
        if not row.get("meal_plan"):
            add_item("info", f"{day}: accommodation missing meal plan — {name}")
        elif "without breakfast" in str(row.get("meal_plan", "")).lower():
            add_item("info", f"{day}: accommodation is marked without breakfast — {name}")

    for row in self_arranged:
        title = row.get("title", "Self-arranged travel")
        add_item("warning", f"{row.get('day', '')}: self-arranged travel shown — {title}")

    if optional_rows:
        add_item("info", f"Optional add-ons detected: {len(optional_rows)} item(s)")

    for day, rows in grouped_days.items():
        activity_count = sum(1 for row in rows if get_row_type(row) == "Activity")
        block_count = len(rows)
        if block_count >= 7 or activity_count >= 3:
            add_item("warning", f"{day}: busy day — review page balance before export")

    return items


def get_itinerary_health(review_items):
    warnings = sum(1 for item in review_items if item.get("severity") == "warning")
    if warnings == 0 and len(review_items) <= 1:
        return "Excellent"
    if warnings <= 2:
        return "Good"
    return "Needs review"


def render_sidebar_review_assistant(parsed_rows, grouped_days, stats):
    review_items = build_review_items(parsed_rows, grouped_days)
    health = get_itinerary_health(review_items)

    st.subheader("Itinerary health")
    if health == "Excellent":
        st.success("Excellent")
    elif health == "Good":
        st.info("Good")
    else:
        st.warning("Needs review")

    st.subheader("Issues to review")
    if review_items:
        for item in review_items[:8]:
            icon = "⚠" if item.get("severity") == "warning" else "•"
            st.caption(f"{icon} {item['message']}")
        if len(review_items) > 8:
            st.caption(f"+ {len(review_items) - 8} more item(s) in the editable itinerary.")
    else:
        st.caption("No practical review issues detected.")

    st.subheader("Ready to export")
    checklist = [
        (stats["days"] > 0, "Days detected"),
        (stats["destinations"] > 0, "Destinations detected"),
        (stats["hotels"] > 0, "Accommodation detected"),
        (True, "Activity details shown inline"),
        (st.session_state.get("pdf_status") == "Ready", "PDF created"),
    ]
    for ok, label in checklist:
        icon = "✓" if ok else "⚠"
        st.caption(f"{icon} {label}")

def render_sidebar_snapshot():
    parsed_rows = st.session_state.get("parsed_rows", [])
    if not parsed_rows:
        st.caption("Generate an itinerary to see stats, quality checks, and creative tools here.")
        return

    edited_rows, grouped_days = get_current_itinerary_state()
    stats = get_itinerary_stats(edited_rows, grouped_days)
    diagnostics_count = len(st.session_state.get("parser_diagnostics", []))

    st.divider()
    st.subheader("Snapshot")
    stat_a, stat_b = st.columns(2)
    stat_a.metric("Days", stats["days"])
    stat_b.metric("Places", stats["destinations"])
    stat_c, stat_d = st.columns(2)
    stat_c.metric("Activities", stats["activities"])
    stat_d.metric("Hotels", stats["hotels"])

    if stats["self_arranged"]:
        st.markdown(f'<div class="sidebar-pill">Self-arranged travel: {stats["self_arranged"]}</div>', unsafe_allow_html=True)
    if stats["optional_rows"]:
        st.markdown(f'<div class="sidebar-pill">Optional add-ons: {stats["optional_rows"]}</div>', unsafe_allow_html=True)

    render_sidebar_review_assistant(edited_rows, grouped_days, stats)
    st.caption(f"PDF status: {st.session_state.get('pdf_status', 'Not created')}")

    st.subheader("Writing assistant")
    st.caption("Runs automatically on generation. Use this again after manual edits if you want to refresh the day text.")
    if st.button("Improve day-to-day text", key="sidebar_assistant_improve_all", use_container_width=True):
        st.session_state.output_edits = apply_rich_writing_to_all_days(
            st.session_state.parsed_rows,
            st.session_state.output_edits,
        )
        mark_output_dirty()
        st.rerun()

    st.subheader("Creative tools")
    suggestions = make_title_suggestions(edited_rows, grouped_days)
    if suggestions:
        index = st.session_state.get("title_suggestion_index", 0) % len(suggestions)
        suggestion = suggestions[index]
        st.caption(f"Title idea: {suggestion}")
        if st.button("Use title idea", use_container_width=True):
            st.session_state.output_edits["trip_title"] = suggestion
            st.session_state.title_suggestion_index = index + 1
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"
            st.rerun()
        if st.button("Try another title", use_container_width=True):
            st.session_state.title_suggestion_index = index + 1
            st.rerun()


def initialise_state():
    defaults = {
        "itinerary_html": "",
        "html_path": None,
        "pdf_bytes": None,
        "parsed_rows": [],
        "output_edits": {},
        "last_generated_raw_text": "",
        "parser_diagnostics": [],
        "pdf_status": "Not created",
        "detail_level": "Rich descriptive",
        "day_page_layout": "Smart compact pages",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_project_json(uploaded_file):
    try:
        data = json.loads(uploaded_file.read().decode("utf-8"))
        raw_text = data.get("raw_text", "")
        output_edits = data.get("output_edits", {})

        parsed_rows = parse_and_normalize_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)

        st.session_state.parsed_rows = parsed_rows
        previous_detail = (output_edits or {}).get("detail_level", "Standard client itinerary")
        st.session_state.output_edits = output_edits or make_output_edit_state(parsed_rows, grouped_days)
        st.session_state.output_edits = refresh_generated_text_for_detail_level(
            parsed_rows,
            st.session_state.output_edits,
            previous_detail,
            "Rich descriptive",
        )
        st.session_state.detail_level = "Rich descriptive"
        st.session_state.output_edits["detail_level"] = "Rich descriptive"
        st.session_state.day_page_layout = st.session_state.output_edits.get("day_page_layout", st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT))
        st.session_state.last_generated_raw_text = raw_text
        st.session_state.pdf_bytes = None

        edited_rows = apply_output_edits(parsed_rows, st.session_state.output_edits)
        edited_grouped_days = group_rows_by_day(edited_rows)
        st.session_state.itinerary_html = build_itinerary_html(edited_rows, edited_grouped_days, st.session_state.output_edits)
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        st.session_state.raw_text_input = raw_text

        st.success("Editable project loaded.")
    except Exception as error:
        st.error("The project JSON could not be loaded.")
        st.exception(error)



def reset_project_state(clear_raw_text=True):
    """Clear the current project and return the app to a clean generation state."""
    for key in [
        "itinerary_html",
        "html_path",
        "pdf_bytes",
        "parsed_rows",
        "output_edits",
        "last_generated_raw_text",
        "parser_diagnostics",
        "_last_visual_editor_result",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.session_state.itinerary_html = ""
    st.session_state.html_path = None
    st.session_state.pdf_bytes = None
    st.session_state.parsed_rows = []
    st.session_state.output_edits = {}
    st.session_state.last_generated_raw_text = ""
    st.session_state.parser_diagnostics = []
    st.session_state.pdf_status = "Not created"

    if clear_raw_text:
        st.session_state.raw_text_input = ""


def rebuild_current_preview(mark_pdf_dirty=True):
    """Rebuild the preview/HTML from the current editable project state."""
    parsed_rows = st.session_state.get("parsed_rows", [])
    output_edits = st.session_state.get("output_edits", {})

    if not parsed_rows or not output_edits:
        return False

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    rebuilt_html = build_itinerary_html(edited_rows, edited_grouped_days, output_edits)

    if rebuilt_html != st.session_state.get("itinerary_html", ""):
        if mark_pdf_dirty:
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"
        st.session_state.itinerary_html = rebuilt_html
    else:
        st.session_state.itinerary_html = rebuilt_html

    st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
    return True



initialise_state()

with st.sidebar:
    st.subheader("Settings")
    current_preset = st.session_state.get("color_preset", "Classic Agent")
    if current_preset not in PRESET_ORDER:
        current_preset = "Classic Agent"

    selected_preset = st.selectbox(
        "Color preset",
        PRESET_ORDER,
        index=PRESET_ORDER.index(current_preset),
        help="Classic Agent keeps the neutral travel-agent look. Booknordics B2C uses a cleaner branded palette.",
    )
    st.session_state.color_preset = selected_preset

    if selected_preset == "Classic Agent":
        st.caption("Warm, neutral, B2B-friendly.")
    else:
        st.caption("Clean, bright, B2C-friendly.")

    selected_detail = "Rich descriptive"
    previous_detail = "Rich descriptive"
    st.session_state.detail_level = selected_detail
    st.caption("Writing style: warm, full and client-facing.")

    current_day_layout = st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    if current_day_layout not in DAY_PAGE_LAYOUTS:
        current_day_layout = DEFAULT_DAY_PAGE_LAYOUT

    selected_day_layout = st.selectbox(
        "Day page layout",
        DAY_PAGE_LAYOUTS,
        index=DAY_PAGE_LAYOUTS.index(current_day_layout),
        help="Keeps each itinerary day on its own A4 page, preparing the layout for day imagery.",
    )
    previous_day_layout = st.session_state.get("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    st.session_state.day_page_layout = selected_day_layout
    st.caption("Premium visual layout: one itinerary day per A4 page.")

    if st.session_state.get("output_edits"):
        st.session_state.output_edits["color_preset"] = selected_preset
        st.session_state.output_edits["day_page_layout"] = selected_day_layout
        st.session_state.output_edits["detail_level"] = "Rich descriptive"
        if previous_day_layout != selected_day_layout:
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"

    show_debug = st.checkbox("Show parser/debug panels", value=False)

    st.divider()
    st.subheader("Project")
    uploaded_project = st.file_uploader("Load editable project JSON", type=["json"])

    if uploaded_project is not None and st.button("Load project", use_container_width=True):
        load_project_json(uploaded_project)
        st.rerun()

    st.divider()
    st.subheader("Project actions")
    st.markdown('<div class="project-action-note">Use these when the preview feels out of sync or when you want to start from a clean slate.</div>', unsafe_allow_html=True)

    if st.button("Refresh preview", use_container_width=True, disabled=not bool(st.session_state.get("parsed_rows"))):
        if rebuild_current_preview(mark_pdf_dirty=True):
            st.success("Preview refreshed.")
        st.rerun()

    if st.button("Generate new itinerary", use_container_width=True):
        reset_project_state(clear_raw_text=True)
        st.rerun()

    render_sidebar_snapshot()

st.markdown(
    f"""
    <div class="app-hero">
        <h1>Itinerary Creator</h1>
        <p>Paste itinerary rows, review the generated output, then export a polished A4 itinerary.</p>
        <p style="font-size: 0.85rem; opacity: 0.65; margin-top: 0.4rem;">Version: {APP_VERSION}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Step 1 — Paste raw itinerary text", expanded=not bool(st.session_state.itinerary_html)):
    st.markdown('<div class="workflow-note">Paste the full itinerary table or copied Excel rows here.</div>', unsafe_allow_html=True)
    raw_text = st.text_area(
        "Raw Excel text",
        height=300,
        placeholder="Paste itinerary rows here...",
        key="raw_text_input",
    )

    if st.button("Generate itinerary", type="primary", use_container_width=True):
        if raw_text.strip():
            diagnostics.reset()
            parsed_rows = parse_and_normalize_itinerary(raw_text)
            grouped_days = group_rows_by_day(parsed_rows)
            duplicate_count = get_duplicate_count(raw_text, parsed_rows)

            st.session_state.parsed_rows = parsed_rows
            st.session_state.output_edits = make_output_edit_state(parsed_rows, grouped_days)
            st.session_state.output_edits = apply_rich_writing_to_all_days(parsed_rows, st.session_state.output_edits)
            st.session_state.last_generated_raw_text = raw_text
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Not created"
            st.session_state.parser_diagnostics = diagnostics.get_warnings()

            edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
            edited_grouped_days = group_rows_by_day(edited_rows)
            st.session_state.itinerary_html = build_itinerary_html(
                edited_rows,
                edited_grouped_days,
                st.session_state.output_edits,
            )
            st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

            st.success(f"Parsed {len(parsed_rows)} itinerary rows across {len(grouped_days)} days. Rich day-to-day wording applied automatically.")

            if duplicate_count:
                st.warning(f"Skipped approximately {duplicate_count} duplicate, continuation, or malformed row(s).")

            overflow_warnings = get_overflow_warnings(edited_grouped_days)
            for warning in overflow_warnings:
                st.warning(warning)

            if st.session_state.html_path:
                st.success("HTML preview prepared.")

        else:
            st.warning("Please paste some itinerary text first.")

if show_debug:
    render_parser_diagnostics_panel()

if show_debug and st.session_state.parsed_rows:
    with st.expander("Debug tools", expanded=False):
        st.dataframe(st.session_state.parsed_rows, use_container_width=True)
        st.write("Day grouping")
        for day, rows in group_rows_by_day(st.session_state.parsed_rows).items():
            st.write(f"{day}: {len(rows)} rows")
            for row in rows:
                st.write(
                    f"- {row.get('type')} / {row.get('effective_type')}: "
                    f"{row.get('title')} ({row.get('city')})"
                )

if st.session_state.parsed_rows and st.session_state.output_edits:
    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)

    with st.expander("Step 2 — Edit proposal directly on A4 pages", expanded=True):
        st.markdown(
            '<div class="workflow-note">Click directly into the A4 pages and type. Use the save button inside the editor before reviewing/exporting.</div>',
            unsafe_allow_html=True,
        )
        render_visual_editor(edited_rows, edited_grouped_days, st.session_state.output_edits, rebuild_preview=rebuild_current_preview, mark_dirty=mark_output_dirty)

    rebuilt_html = build_itinerary_html(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
    )

    if rebuilt_html != st.session_state.itinerary_html:
        st.session_state.pdf_bytes = None
        if st.session_state.itinerary_html:
            st.session_state.pdf_status = "Needs refresh"
        st.session_state.itinerary_html = rebuilt_html
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
    elif st.session_state.itinerary_html and not st.session_state.html_path:
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

if st.session_state.itinerary_html:
    with st.expander("Step 3 — Review final PDF-style preview", expanded=False):
        st.caption("This preview is not editable. It is the final layout check before PDF export.")
        st.html(st.session_state.itinerary_html)

if st.session_state.parsed_rows and st.session_state.output_edits and show_debug:
    with st.expander("Advanced fallback text and image editor", expanded=False):
        render_output_editor(
            st.session_state.parsed_rows,
            group_rows_by_day(apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)),
            st.session_state.output_edits,
        )

if st.session_state.itinerary_html:
    st.subheader("Step 4 — Export")
    st.markdown('<div class="workflow-note">Save your editable project, download the HTML preview, or create a PDF.</div>', unsafe_allow_html=True)

    html_path = Path(st.session_state.html_path) if st.session_state.html_path else None
    project_data = {
        "app_version": APP_VERSION,
        "raw_text": st.session_state.get("last_generated_raw_text", ""),
        "output_edits": st.session_state.get("output_edits", {}),
    }

    export_col_1, export_col_2, export_col_3, export_col_4 = st.columns(4)

    with export_col_1:
        st.download_button(
            "Download project JSON",
            data=json.dumps(project_data, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="itinerary_project.json",
            mime="application/json",
            use_container_width=True,
        )

    with export_col_2:
        if html_path and html_path.exists():
            with open(html_path, "rb") as html_file:
                st.download_button(
                    label="Download HTML",
                    data=html_file,
                    file_name="itinerary_preview.html",
                    mime="text/html",
                    use_container_width=True,
                )
        else:
            st.button("Download HTML", disabled=True, use_container_width=True)
            st.caption("HTML file not available.")

    with export_col_3:
        if st.button("Create PDF", use_container_width=True):
            try:
                with st.spinner("Creating PDF..."):
                    pdf_path = save_pdf_file(html_path)
                    if pdf_path is None:
                        st.session_state.pdf_bytes = None
                        st.session_state.pdf_status = "PDF failed"
                    else:
                        st.session_state.pdf_bytes = Path(pdf_path).read_bytes()
                        st.session_state.pdf_status = "Ready"

                if st.session_state.pdf_bytes:
                    st.success("PDF created. Use the download button.")

            except Exception as error:
                st.session_state.pdf_status = "PDF failed"
                st.error(
                    "PDF export failed in this environment. The itinerary preview and HTML download still work."
                )
                with st.expander("PDF export error details"):
                    st.exception(error)

    with export_col_4:
        if st.session_state.pdf_bytes:
            st.download_button(
                label="Download PDF",
                data=st.session_state.pdf_bytes,
                file_name="itinerary_preview.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("Download PDF", disabled=True, use_container_width=True)
            st.caption(st.session_state.get("pdf_status", "Not created"))
