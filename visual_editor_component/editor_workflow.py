"""Visual editor payload and save workflow."""

import json
from pathlib import Path

import streamlit as st

from generator import (
    create_day_intro,
    create_day_title,
    create_destinations_line,
    create_trip_subtitle,
    create_trip_title,
    get_primary_city,
)
from images.app_image_selection import (
    get_day_image_choice,
    get_day_image_crop_focus,
    image_to_data_uri,
    list_city_image_options,
    normalize_crop_focus,
    select_day_images_with_overrides,
)
from ui.day_rendering import build_day_blocks, get_detail_level_name
from ui.editor_sanitizer import clean_visual_editor_html
from visual_editor_component.editor_bridge import render_visual_page_editor


def build_visual_editor_payload(parsed_rows, grouped_days, output_edits):
    """Build the editable A4-page payload used by the visual editor component."""
    image_matches = select_day_images_with_overrides(grouped_days, output_edits)
    payload_days = []

    for day, rows in grouped_days.items():
        day_edits = (output_edits or {}).get("days", {}).get(day, {})
        city = day_edits.get("city") or get_primary_city(rows)
        match = image_matches.get(day)
        image_path = match.get("path") if match else ""
        image_obj = {
            "mode": get_day_image_choice(output_edits, day).get("mode", "auto"),
            "path": image_path or "",
            "name": Path(image_path).name if image_path else "",
            "data_uri": image_to_data_uri(image_path) if image_path else "",
            "crop_focus": get_day_image_crop_focus(output_edits, day),
            "options": [
                {"path": str(path), "name": path.name}
                for path in list_city_image_options(city)
            ],
        }

        blocks_html = day_edits.get("blocks_html")
        if not blocks_html:
            blocks_html = "".join(block["html"] for block in build_day_blocks(rows))

        payload_days.append({
            "day": day,
            "label": day,
            "title": day_edits.get("title") or create_day_title(rows),
            "city": city,
            "intro": day_edits.get("intro") or create_day_intro(rows, detail_level=get_detail_level_name(output_edits)),
            "blocks_html": blocks_html,
            "image": image_obj,
        })

    return {
        "cover": {
            "trip_title": output_edits.get("trip_title", create_trip_title(parsed_rows, grouped_days)),
            "trip_subtitle": output_edits.get("trip_subtitle", create_trip_subtitle(parsed_rows, grouped_days)),
            "destinations_line": output_edits.get("destinations_line", create_destinations_line(parsed_rows)),
        },
        "days": payload_days,
        "final_pages": {
            "whats_included_text": output_edits.get("whats_included_text", ""),
            "whats_not_included_text": output_edits.get("whats_not_included_text", ""),
            "important_travel_notes_text": output_edits.get("important_travel_notes_text", ""),
        },
    }


def apply_visual_editor_result(result, output_edits, mark_dirty=None):
    """Persist visual editor edits into the normal output_edits structure."""
    if not result:
        return False
    try:
        data = json.loads(result) if isinstance(result, str) else result
    except Exception:
        st.warning("Visual editor edits could not be read. Please try saving again.")
        return False

    cover = data.get("cover", {}) or {}
    for key in ["trip_title", "trip_subtitle", "destinations_line"]:
        if key in cover:
            output_edits[key] = str(cover.get(key, "")).strip()

    day_payloads = data.get("days", []) or []
    for day_payload in day_payloads:
        day = day_payload.get("day")
        if not day:
            continue
        day_edits = output_edits.setdefault("days", {}).setdefault(day, {})
        for key in ["title", "city", "intro"]:
            if key in day_payload:
                day_edits[key] = str(day_payload.get(key, "")).strip()
        if "blocks_html" in day_payload:
            cleaned_blocks = clean_visual_editor_html(day_payload.get("blocks_html", ""))
            if cleaned_blocks:
                day_edits["blocks_html"] = cleaned_blocks

        image_payload = day_payload.get("image") or {}
        if image_payload:
            choice = get_day_image_choice(output_edits, day)
            mode = str(image_payload.get("mode") or choice.get("mode", "auto")).strip().lower()
            if mode not in {"auto", "manual", "none"}:
                mode = "auto"
            choice["mode"] = mode
            choice["crop_focus"] = normalize_crop_focus(image_payload.get("crop_focus", choice.get("crop_focus", "top")))
            if mode == "manual":
                choice["path"] = str(image_payload.get("path") or choice.get("path", "")).strip()
            elif mode in {"auto", "none"}:
                choice["path"] = ""

    final_pages = data.get("final_pages", {}) or {}
    for key in ["whats_included_text", "whats_not_included_text", "important_travel_notes_text"]:
        if key in final_pages:
            output_edits[key] = str(final_pages.get(key, "")).strip()

    if mark_dirty:
        mark_dirty()
    return True


def render_visual_editor(parsed_rows, grouped_days, output_edits, rebuild_preview=None, mark_dirty=None):
    """Render and process the direct editable A4-page editor."""
    payload = build_visual_editor_payload(parsed_rows, grouped_days, output_edits)
    result = render_visual_page_editor(payload, key="visual_page_editor")
    if result and result != st.session_state.get("_last_visual_editor_result"):
        st.session_state["_last_visual_editor_result"] = result
        if apply_visual_editor_result(result, output_edits, mark_dirty=mark_dirty):
            if rebuild_preview:
                rebuild_preview(mark_pdf_dirty=True)
            st.success("Edits saved to preview and PDF export.")
            st.rerun()
