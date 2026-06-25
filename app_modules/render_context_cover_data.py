"""Cover-page source data preparation for itinerary render context."""

from __future__ import annotations

from typing import Any

from app_modules.display_settings import get_color_preset, get_color_preset_name
from app_modules.itinerary_html_sections import balanced_cover_subtitle_html
from itinerary_generation.cover_assets import resolve_cover_background
from itinerary_generation.cover_route import clean_or_create_cover_route_line, cover_route_html
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.date_resolver import get_trip_date_range_text
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from ui.picture_workflow import pictures_are_added


def _safe_label(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def build_cover_context_data(parsed_rows, grouped_days, output_edits: dict[str, Any], editor_draft: dict[str, Any]) -> dict[str, Any]:
    """Build cover/theme fields used by both HTML preview and typed PDF export."""

    typed_cover = editor_draft.get("cover", {}) if isinstance(editor_draft.get("cover"), dict) else {}
    include_picture_data = pictures_are_added(output_edits)
    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=include_picture_data)
    summary_image = resolve_cover_background(parsed_rows, output_edits, key="summary_image", include_image_data=include_picture_data)

    trip_title = typed_cover.get("trip_title") or output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    cover_title_class = "cover-title"
    if len(str(trip_title)) <= 24:
        cover_title_class += " cover-title-fit"
    elif len(str(trip_title)) <= 32:
        cover_title_class += " cover-title-balanced"

    trip_subtitle = typed_cover.get("trip_subtitle") or output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    saved_destinations_line = typed_cover.get("destinations_line") or output_edits.get("destinations_line")
    destinations_line = clean_or_create_cover_route_line(parsed_rows, saved_destinations_line or create_destinations_line(parsed_rows))

    return {
        "preset_name": get_color_preset_name(output_edits),
        "colors": get_color_preset(output_edits),
        "colors_json": "",
        "cover_theme": cover_theme,
        "cover_kicker": typed_cover.get("cover_kicker") or output_edits.get("cover_kicker") or "Travel Itinerary",
        "cover_route_label": _safe_label(typed_cover.get("route_label") or output_edits.get("route_label"), "Route"),
        "cover_title_class": cover_title_class,
        "trip_title": trip_title,
        "trip_subtitle": trip_subtitle,
        "trip_subtitle_html": balanced_cover_subtitle_html(trip_subtitle),
        "trip_dates": typed_cover.get("trip_dates") or output_edits.get("trip_dates") or get_trip_date_range_text(parsed_rows),
        "cover_background_data_uri": cover_theme.get("background_data_uri", ""),
        "cover_background_path": cover_theme.get("background_path", ""),
        "cover_crop_focus": cover_theme.get("background_crop_focus", "top"),
        "summary_background_data_uri": summary_image.get("data_uri", ""),
        "summary_background_path": summary_image.get("path", ""),
        "summary_crop_focus": summary_image.get("crop_focus", "top"),
        "destinations_line": destinations_line,
        "destinations_line_html": cover_route_html(destinations_line),
    }


__all__ = ["_safe_label", "build_cover_context_data"]
