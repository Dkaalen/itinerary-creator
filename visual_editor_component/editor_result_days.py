"""Apply visual-editor generated-day text and image payload fields."""

from images.app_image_selection import (
    get_day_image_choice,
    normalize_crop_focus,
    save_data_uri_day_image,
)
from ui.editor_sanitizer import clean_visual_editor_html


def _payload_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if value is None:
        return default
    return bool(value)


def apply_day_payloads(data, output_edits):
    day_payloads = data.get("days", []) or []
    for day_payload in day_payloads:
        day = day_payload.get("day")
        if not day:
            continue
        day_edits = output_edits.setdefault("days", {}).setdefault(day, {})
        for key in ["title", "city", "date"]:
            if key in day_payload:
                day_edits[key] = str(day_payload.get(key, "")).strip()
        if "intro" in day_payload:
            day_edits["intro"] = str(day_payload.get("intro", "")).strip()
            day_edits["intro_manual_override"] = _payload_bool(
                day_payload.get("intro_manual_override"),
                default=True,
            )
            if "intro_generated_value" in day_payload:
                day_edits["intro_generated_value"] = str(day_payload.get("intro_generated_value", "")).strip()
            if "intro_generator_version" in day_payload:
                day_edits["intro_generator_version"] = str(day_payload.get("intro_generator_version", "")).strip()
            if "intro_source_signature" in day_payload:
                day_edits["intro_source_signature"] = str(day_payload.get("intro_source_signature", "")).strip()
        if "blocks_html" in day_payload:
            # A present blocks_html field is an explicit editor decision only
            # when the browser marks it as a manual block edit. Full generated
            # commits carry blocks_manual_override=false so typed PDF rendering
            # can stay active.
            day_edits["blocks_html"] = clean_visual_editor_html(day_payload.get("blocks_html", ""))
            day_edits["blocks_manual_override"] = _payload_bool(
                day_payload.get("blocks_manual_override"),
                default=True,
            )
            if "blocks_html_generated_value" in day_payload:
                day_edits["blocks_html_generated_value"] = clean_visual_editor_html(day_payload.get("blocks_html_generated_value", ""))
            if "blocks_html_generator_version" in day_payload:
                day_edits["blocks_html_generator_version"] = str(day_payload.get("blocks_html_generator_version", "")).strip()

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
