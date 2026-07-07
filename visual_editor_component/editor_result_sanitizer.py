"""Sanitize typed visual-editor draft fields before persistence."""

import json

from itinerary_generation.cover_assets import normalize_cover_crop_focus
from ui.editor_sanitizer import clean_visual_editor_html, normalize_final_list_html
from visual_editor_component.editor_result_codec import _normalize_route_edit


def _sanitize_cover_image_payload(value: dict) -> dict:
    raw = value if isinstance(value, dict) else {}
    mode_text = str(raw.get("mode") or "auto").strip().lower()
    if bool(raw.get("removed", False)) or mode_text in {"none", "removed", "remove", "deleted", "delete"}:
        mode = "none"
    elif mode_text == "manual":
        mode = "manual"
    else:
        mode = "auto"
    path = str(raw.get("path") or "").strip() if mode == "manual" else ""
    choice = {
        "mode": mode,
        "path": path,
        "crop_focus": normalize_cover_crop_focus(raw.get("crop_focus") or "top"),
    }
    if bool(raw.get("removed", False)):
        choice["removed"] = True
    return choice


def _sanitize_editor_draft(editor_draft):
    """Clean typed editor draft values before storing/mirroring them."""
    if not isinstance(editor_draft, dict):
        return {}
    cleaned = json.loads(json.dumps(editor_draft))
    cover = cleaned.get("cover") if isinstance(cleaned.get("cover"), dict) else {}
    for key, value in list(cover.items()):
        if key in {"cover_image", "summary_image"}:
            cover[key] = _sanitize_cover_image_payload(value)
            continue
        text = str(value or "").strip()
        cover[key] = _normalize_route_edit(text) if key == "destinations_line" else text
    cleaned["cover"] = cover

    for day in cleaned.get("days") or []:
        if not isinstance(day, dict):
            continue
        for key in ("title", "city", "intro", "label", "date"):
            if key in day:
                day[key] = str(day.get(key, "")).strip()
        for block in day.get("blocks") or []:
            if isinstance(block, dict):
                block["content_html"] = clean_visual_editor_html(block.get("content_html", block.get("html", "")) or "")

    for section in cleaned.get("final_sections") or []:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id", ""))
        for page in section.get("pages") or []:
            if not isinstance(page, dict):
                continue
            html = page.get("content_html", page.get("html", "")) or ""
            page["content_html"] = normalize_final_list_html(html) if section_id == "whats_not_included" else clean_visual_editor_html(html)
        if "content_html" in section:
            html = section.get("content_html", "") or ""
            section["content_html"] = normalize_final_list_html(html) if section_id == "whats_not_included" else clean_visual_editor_html(html)
        if "text" in section:
            section["text"] = str(section.get("text", "")).strip()
    return cleaned
