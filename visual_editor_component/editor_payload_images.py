"""Image payload helpers for the visual editor."""

from pathlib import Path

from images.app_image_selection import (
    audit_day_image_matches,
    get_day_image_choice,
    get_day_image_crop_focus,
    get_image_preview_for_path,
    list_replacement_image_options_for_rows,
    select_day_images_with_overrides,
)
from itinerary_generation.cover_assets import resolve_cover_background


OPTION_PREVIEW_LIMIT = 4
DAY_REPLACEMENT_OPTION_LIMIT = 8


def _with_option_previews(options, *, preview_limit: int = OPTION_PREVIEW_LIMIT):
    enriched = []
    for index, option in enumerate(options or []):
        item = dict(option or {})
        path = item.get("path")
        if path and not item.get("preview_data_uri") and index < preview_limit:
            item["preview_data_uri"] = get_image_preview_for_path(path, option=True)
        else:
            item.setdefault("preview_data_uri", "")
        enriched.append(item)
    return enriched


def _editor_cover_image_payload(parsed_rows, output_edits, key: str, *, pictures_added: bool) -> dict:
    image = resolve_cover_background(parsed_rows, output_edits, key=key, include_image_data=False)
    if not pictures_added:
        image["data_uri"] = ""
        image["auto_data_uri"] = ""
        return image
    if image.get("path"):
        image["data_uri"] = get_image_preview_for_path(image.get("path"))
    if image.get("auto_path"):
        image["auto_data_uri"] = get_image_preview_for_path(image.get("auto_path"))
    image["options"] = _with_option_previews(image.get("options") or [])
    return image


def build_day_image_context(grouped_days, output_edits, *, pictures_added: bool):
    image_matches = select_day_images_with_overrides(grouped_days, output_edits) if pictures_added else {}
    image_warnings = audit_day_image_matches(grouped_days, image_matches, output_edits) if pictures_added else ()
    image_warnings_by_day = {}
    for warning in image_warnings:
        image_warnings_by_day.setdefault(warning.day, []).append({
            "code": warning.code,
            "severity": warning.severity,
            "message": warning.message,
            "path": warning.path,
        })
    return image_matches, image_warnings, image_warnings_by_day


def build_day_image_payload(day, rows, output_edits, *, pictures_added: bool, image_matches, image_warnings_by_day):
    if pictures_added:
        match = image_matches.get(day)
        image_path = match.get("path") if match else ""
        preview_data_uri = get_image_preview_for_path(image_path) if image_path else ""
        options = _with_option_previews(list_replacement_image_options_for_rows(day, rows, limit=DAY_REPLACEMENT_OPTION_LIMIT))
        return {
            "mode": get_day_image_choice(output_edits, day).get("mode", "auto"),
            "path": image_path or "",
            "name": Path(image_path).name if image_path else "",
            "data_uri": preview_data_uri,
            "auto_path": image_path or "",
            "auto_name": Path(image_path).name if image_path else "",
            "auto_data_uri": preview_data_uri,
            "crop_focus": get_day_image_crop_focus(output_edits, day),
            "options": options,
            "warnings": image_warnings_by_day.get(day, []),
        }
    return {
        "mode": "pending",
        "path": "",
        "name": "",
        "data_uri": "",
        "auto_path": "",
        "auto_name": "",
        "auto_data_uri": "",
        "crop_focus": "top",
        "options": [],
        "pictures_pending": True,
        "warnings": [],
    }


def build_cover_image_payloads(parsed_rows, output_edits, *, pictures_added: bool):
    return (
        _editor_cover_image_payload(parsed_rows, output_edits, "cover_image", pictures_added=pictures_added),
        _editor_cover_image_payload(parsed_rows, output_edits, "summary_image", pictures_added=pictures_added),
    )
