from pathlib import Path

import streamlit as st

from images.diagnostics import image_bank_debug_payload, image_bank_status_summary

from itinerary_generation.common import get_primary_city, group_rows_by_day
from ui.output_edits import apply_output_edits, mark_output_dirty
from images.app_image_selection import (
    CROP_FOCUS_LABELS,
    CROP_FOCUS_OPTIONS,
    ensure_runtime_image_bank,
    ensure_runtime_image_bank_status,
    get_day_image_choice,
    image_bank_status,
    list_replacement_image_options,
    normalize_crop_focus,
    normalize_path_key,
    audit_day_image_matches,
    save_uploaded_day_image,
    select_day_images_with_overrides,
)


def get_current_day_image_matches(output_edits):
    parsed_rows = st.session_state.get("parsed_rows", [])
    if not parsed_rows:
        return {}
    edited_rows = apply_output_edits(parsed_rows, output_edits)
    return select_day_images_with_overrides(group_rows_by_day(edited_rows), output_edits)


def get_current_day_image_warnings(output_edits, image_matches=None):
    parsed_rows = st.session_state.get("parsed_rows", [])
    if not parsed_rows:
        return ()
    edited_rows = apply_output_edits(parsed_rows, output_edits)
    grouped_days = group_rows_by_day(edited_rows)
    matches = image_matches if image_matches is not None else select_day_images_with_overrides(grouped_days, output_edits)
    return audit_day_image_matches(grouped_days, matches, output_edits)




def render_image_bank_status_notice():
    status = image_bank_status()
    if status.get("full_bank_found"):
        st.success(image_bank_status_summary(status) + ".")
    else:
        st.error(status.get("blocking_message") or "Full destination image bank is missing.")
        st.caption("Expected source: Dkaalen/itinerary-image-bank/image_bank_full")
        if status.get("runtime_bootstrap_allowed"):
            if st.button("Fetch image bank from GitHub", key="fetch_runtime_image_bank", use_container_width=False):
                setup_status = ensure_runtime_image_bank_status()
                if setup_status.get("ok"):
                    st.success(f"Image bank fetched: {setup_status.get('path')}")
                    st.rerun()
                else:
                    st.warning(setup_status.get("message") or "Could not fetch the image bank automatically.")
                    if setup_status.get("error"):
                        with st.expander("Image-bank setup error details"):
                            st.code(str(setup_status.get("error")), language=None)
        else:
            st.warning("Runtime image-bank fetching is disabled. Set ITINERARY_IMAGE_BANK_FULL to the local image_bank_full folder.")

    with st.expander("Image-bank diagnostics", expanded=False):
        st.json(image_bank_debug_payload(status.get("paths") or []))

    return status


def _warnings_by_day(warnings):
    grouped = {}
    for warning in warnings or ():
        grouped.setdefault(warning.day, []).append(warning)
    return grouped


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

    options = list_replacement_image_options(city)
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
    image_warnings_by_day = _warnings_by_day(get_current_day_image_warnings(output_edits, image_matches))

    with st.expander("Picture review & controls", expanded=True):
        render_image_bank_status_notice()
        st.caption(
            "Review the pictures before PDF export. Select a day, then remove, replace, upload, or adjust the crop focus. "
            "The final PDF uses the full-width, bottom-edge image layout."
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
                if image_warnings_by_day.get(day):
                    st.caption("Needs image review")
                if st.button("Edit picture", key=f"picture_studio_open_{day}", use_container_width=True):
                    st.session_state.active_image_day = day
                    st.rerun()

        active_day = st.session_state.get("active_image_day", days[0])
        active_warnings = image_warnings_by_day.get(active_day, [])
        if active_warnings:
            for warning in active_warnings:
                if warning.severity == "error":
                    st.error(warning.message)
                elif warning.severity == "info":
                    st.info(warning.message)
                else:
                    st.warning(warning.message)
        st.divider()
        render_day_picture_action_panel(
            active_day,
            grouped_days[active_day],
            output_edits,
            current_match=image_matches.get(active_day),
            key_prefix="picture_studio_active",
        )
