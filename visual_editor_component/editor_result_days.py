"""Apply visual-editor generated-day text and image payload fields."""

from images.app_image_selection import (
    get_day_image_choice,
    normalize_crop_focus,
    save_data_uri_day_image,
)
from ui.editor_sanitizer import clean_visual_editor_html


def apply_day_payloads(data, output_edits):
    day_payloads = data.get("days", []) or []
    for day_payload in day_payloads:
        day = day_payload.get("day")
        if not day:
            continue
        day_edits = output_edits.setdefault("days", {}).setdefault(day, {})
        for key in ["title", "city", "intro", "date"]:
            if key in day_payload:
                day_edits[key] = str(day_payload.get(key, "")).strip()
        if "blocks_html" in day_payload:
            # A present blocks_html field is an explicit editor decision. Store
            # even an empty string so clearing a day block does not regenerate
            # the old generated travel/activity content during PDF export.
            day_edits["blocks_html"] = clean_visual_editor_html(day_payload.get("blocks_html", ""))

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
