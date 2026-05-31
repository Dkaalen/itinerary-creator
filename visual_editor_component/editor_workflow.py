"""Visual editor payload and save workflow."""

import json
from pathlib import Path

import streamlit as st

from itinerary_generation.common import get_primary_city
from itinerary_generation.day_text import create_day_intro, create_travel_route_label
from itinerary_generation.titles import (
    create_day_title,
    create_destinations_line,
    create_trip_subtitle,
    create_trip_title,
)
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.date_resolver import get_day_date_text, get_trip_date_range_text
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.summaries import create_journey_arc, create_trip_glance
from images.app_image_selection import (
    get_day_image_choice,
    get_day_image_crop_focus,
    get_image_preview_for_path,
    list_replacement_image_options_for_rows,
    normalize_crop_focus,
    save_data_uri_day_image,
    select_day_images_with_overrides,
)
from ui.day_pages import render_inclusion_sections_inner_html
from ui.day_blocks import build_day_blocks
from ui.render_helpers import get_detail_level_name
from ui.editor_sanitizer import clean_visual_editor_html
from visual_editor_component.editor_bridge import render_visual_page_editor


def _get_trip_glance(parsed_rows, grouped_days, output_edits):
    generated = create_trip_glance(parsed_rows, grouped_days)
    saved = (output_edits or {}).get("trip_glance") or {}
    if isinstance(saved, dict):
        for key, value in saved.items():
            if key in generated:
                generated[key] = value
    return generated


def _get_journey_arc(grouped_days, output_edits):
    saved = (output_edits or {}).get("journey_arc")
    if isinstance(saved, list) and saved:
        clean_rows = []
        for row in saved:
            if isinstance(row, dict):
                clean_rows.append({
                    "chapter": str(row.get("chapter", "")).strip(),
                    "days": str(row.get("days", "")).strip(),
                    "experience": str(row.get("experience", "")).strip(),
                })
        if clean_rows:
            return clean_rows
    return create_journey_arc(grouped_days)


def _build_generated_inclusions_html(parsed_rows, grouped_days):
    return render_inclusion_sections_inner_html(create_categorized_inclusions(parsed_rows, grouped_days))


def _normalize_route_edit(value):
    """Normalize editable cover-route text back to a single separator-delimited line."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", " · ")
    parts = [part.strip() for part in text.split("·") if part.strip()]
    return " · ".join(parts)


def build_visual_editor_payload(parsed_rows, grouped_days, output_edits):
    """Build the editable A4-page payload used by the visual editor component."""
    image_matches = select_day_images_with_overrides(grouped_days, output_edits)
    payload_days = []

    for day, rows in grouped_days.items():
        day_edits = (output_edits or {}).get("days", {}).get(day, {})
        city = day_edits.get("city") or create_travel_route_label(rows) or get_primary_city(rows)
        match = image_matches.get(day)
        image_path = match.get("path") if match else ""
        options = list_replacement_image_options_for_rows(day, rows)
        image_obj = {
            "mode": get_day_image_choice(output_edits, day).get("mode", "auto"),
            "path": image_path or "",
            "name": Path(image_path).name if image_path else "",
            "data_uri": get_image_preview_for_path(image_path) if image_path else "",
            "auto_path": image_path or "",
            "auto_name": Path(image_path).name if image_path else "",
            "auto_data_uri": get_image_preview_for_path(image_path) if image_path else "",
            "crop_focus": get_day_image_crop_focus(output_edits, day),
            "options": options,
        }

        blocks_html = day_edits.get("blocks_html")
        if not blocks_html:
            blocks_html = "".join(block["html"] for block in build_day_blocks(rows))

        payload_days.append({
            "day": day,
            "label": day,
            "date": get_day_date_text(rows),
            "title": day_edits.get("title") or create_day_title(rows),
            "city": city,
            "intro": day_edits.get("intro") or create_day_intro(rows, detail_level=get_detail_level_name(output_edits)),
            "blocks_html": blocks_html,
            "image": image_obj,
        })

    generated_inclusions_html = _build_generated_inclusions_html(parsed_rows, grouped_days)
    cover_theme = get_cover_theme(parsed_rows, output_edits)

    return {
        "cover": {
            "cover_kicker": output_edits.get("cover_kicker", "Travel Itinerary"),
            "cover_season": cover_theme.get("season", "summer"),
            "cover_background_data_uri": cover_theme.get("background_data_uri", ""),
            "cover_ink": cover_theme.get("ink", "#1f3446"),
            "cover_muted": cover_theme.get("muted", "#7b746c"),
            "cover_accent": cover_theme.get("accent", "#b89555"),
            "trip_title": output_edits.get("trip_title", create_trip_title(parsed_rows, grouped_days)),
            "trip_subtitle": output_edits.get("trip_subtitle", create_trip_subtitle(parsed_rows, grouped_days)),
            "trip_dates": output_edits.get("trip_dates") or get_trip_date_range_text(parsed_rows),
            "destinations_line": output_edits.get("destinations_line", create_destinations_line(parsed_rows)),
        },
        "summary": {
            "trip_glance": _get_trip_glance(parsed_rows, grouped_days, output_edits),
            "journey_arc": _get_journey_arc(grouped_days, output_edits),
        },
        "days": payload_days,
        "final_pages": {
            "whats_included_html": output_edits.get("whats_included_html") or generated_inclusions_html,
            "whats_included_text": output_edits.get("whats_included_text", ""),
            "whats_not_included_text": output_edits.get("whats_not_included_text", ""),
            "important_travel_notes_text": output_edits.get("important_travel_notes_text", ""),
        },
    }


def _decode_visual_editor_result(result):
    """Decode visual editor payloads, including export-commit wrappers."""
    data = json.loads(result) if isinstance(result, str) else result
    if isinstance(data, dict) and "payload" in data and "commit_nonce" in data:
        return data.get("payload") or {}, str(data.get("commit_nonce") or "")
    return data, ""


def apply_visual_editor_result(result, output_edits, mark_dirty=None):
    """Persist visual editor edits into the normal output_edits structure."""
    if not result:
        return False
    try:
        data, commit_nonce = _decode_visual_editor_result(result)
    except Exception:
        st.warning("Visual editor edits could not be read. Please try saving again.")
        return False
    if not isinstance(data, dict):
        return False

    cover = data.get("cover", {}) or {}
    for key in ["cover_kicker", "trip_title", "trip_subtitle", "destinations_line"]:
        if key in cover:
            value = str(cover.get(key, "")).strip()
            output_edits[key] = _normalize_route_edit(value) if key == "destinations_line" else value

    summary = data.get("summary", {}) or {}
    if isinstance(summary.get("trip_glance"), dict):
        output_edits["trip_glance"] = {
            str(key).strip(): str(value).strip()
            for key, value in summary.get("trip_glance", {}).items()
            if str(key).strip()
        }
    if isinstance(summary.get("journey_arc"), list):
        output_edits["journey_arc"] = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in summary.get("journey_arc", [])
            if isinstance(row, dict)
        ]

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

            upload = image_payload.get("upload") or {}
            if mode == "manual" and upload.get("data_uri"):
                saved_path = save_data_uri_day_image(
                    upload.get("data_uri", ""),
                    upload.get("filename", "uploaded_image.jpg"),
                    day_edits.get("city") or day_payload.get("city", ""),
                    upload.get("season", "Summer"),
                    upload.get("label", ""),
                )
                choice["path"] = saved_path or str(image_payload.get("path") or choice.get("path", "")).strip()
            elif mode == "manual":
                choice["path"] = str(image_payload.get("path") or choice.get("path", "")).strip()
            elif mode in {"auto", "none"}:
                choice["path"] = ""

    final_pages = data.get("final_pages", {}) or {}
    if "whats_included_html" in final_pages:
        output_edits["whats_included_html"] = clean_visual_editor_html(final_pages.get("whats_included_html", ""))
        output_edits["whats_included_text"] = ""
    for key in ["whats_included_text", "whats_not_included_text", "important_travel_notes_text"]:
        if key in final_pages and key != "whats_included_text":
            output_edits[key] = str(final_pages.get(key, "")).strip()

    if commit_nonce:
        st.session_state["_visual_editor_last_applied_commit_nonce"] = commit_nonce

    if mark_dirty:
        mark_dirty()
    return True


def render_visual_editor(parsed_rows, grouped_days, output_edits, rebuild_preview=None, mark_dirty=None):
    """Render and process the direct editable A4-page editor.

    Returns True only when a saved editor payload was applied. The app can then
    skip any additional rebuild based on the pre-save rows from the same rerun.
    """
    payload = build_visual_editor_payload(parsed_rows, grouped_days, output_edits)
    commit_nonce = st.session_state.get("_visual_editor_commit_nonce")
    result = render_visual_page_editor(payload, key="visual_page_editor", commit_nonce=commit_nonce)
    if result and result != st.session_state.get("_last_visual_editor_result"):
        st.session_state["_last_visual_editor_result"] = result
        if apply_visual_editor_result(result, output_edits, mark_dirty=mark_dirty):
            if rebuild_preview:
                rebuild_preview(mark_pdf_dirty=True)
            applied_nonce = st.session_state.get("_visual_editor_last_applied_commit_nonce")
            if applied_nonce and str(applied_nonce) == str(st.session_state.get("_pdf_after_visual_edit_commit_nonce", "")):
                st.session_state["_visual_editor_export_commit_ready"] = True
            else:
                st.success("Edits saved to preview and PDF export.")
            return True
    return False
