import json
from collections import OrderedDict

from itinerary_generation.inclusions import create_whats_included, create_whats_not_included
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.cover_route import cover_route_html
from itinerary_generation.summaries import create_journey_arc, create_trip_glance
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.date_resolver import get_trip_date_range_text
from ui.day_pages import (
    render_day_pages,
    render_split_list_pages,
    render_categorized_inclusions_pages,
    render_custom_html_final_page,
    render_custom_html_final_pages,
    render_text_paragraph_page,
)
from ui.final_pages import (
    create_optional_addons,
    get_important_travel_notes,
    render_optional_addons_pages,
)
from itinerary_generation.common import is_optional_row
from ui.render_helpers import esc, text_to_list
from ui.picture_workflow import pictures_are_added
from app_modules.display_settings import get_color_preset, get_color_preset_name
from app_modules.itinerary_html_sections import (
    balanced_cover_subtitle_html,
    render_cover_page,
    render_summary_page,
)
from app_modules.itinerary_html_styles import build_preview_style


def _balanced_cover_subtitle_html(subtitle: str) -> str:
    """Compatibility wrapper for tests/older imports."""
    return balanced_cover_subtitle_html(subtitle)


def _balanced_cover_destinations_html(destinations_line: str) -> str:
    """Compatibility wrapper for tests/older imports."""
    return cover_route_html(destinations_line)


def _grouped_days_with_day_optional_rows(grouped_days, parsed_rows):
    """Return a render-only copy of grouped days with optional rows appended.

    Core grouping intentionally excludes optional rows so duration, route, journey
    arc and main inclusions stay based on confirmed itinerary content.  Day pages
    still need to show explicit optional experiences in context, so this helper
    adds them only to the render copy used by ``render_day_pages``.
    """

    rendered = OrderedDict((day, list(rows)) for day, rows in grouped_days.items())
    for row in parsed_rows or []:
        if not is_optional_row(row):
            continue
        day = row.get("day", "")
        if day in rendered:
            rendered[day].append(row)
    return rendered


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    output_edits = output_edits or {}
    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)
    colors_json = esc(json.dumps(colors))

    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=pictures_are_added(output_edits))
    cover_kicker = output_edits.get("cover_kicker") or "Travel Itinerary"
    trip_title = output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    cover_title_class = "cover-title"
    if len(str(trip_title)) <= 24:
        cover_title_class += " cover-title-fit"
    elif len(str(trip_title)) <= 32:
        cover_title_class += " cover-title-balanced"
    trip_subtitle = output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    trip_subtitle_html = _balanced_cover_subtitle_html(trip_subtitle)
    trip_dates = output_edits.get("trip_dates") or get_trip_date_range_text(parsed_rows)
    cover_background_data_uri = cover_theme.get("background_data_uri", "")
    cover_background_path = cover_theme.get("background_path", "")
    destinations_line = output_edits.get("destinations_line") or create_destinations_line(parsed_rows)
    destinations_line_html = cover_route_html(destinations_line)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    saved_trip_glance = output_edits.get("trip_glance") or {}
    if isinstance(saved_trip_glance, dict):
        for label, value in saved_trip_glance.items():
            if label in trip_glance:
                trip_glance[label] = value

    saved_journey_arc = output_edits.get("journey_arc")
    if isinstance(saved_journey_arc, list) and saved_journey_arc:
        journey_arc = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in saved_journey_arc
            if isinstance(row, dict)
        ]
    else:
        journey_arc = create_journey_arc(grouped_days)

    manual_whats_included = text_to_list(output_edits.get("whats_included_text", ""))
    categorized_inclusions = create_categorized_inclusions(parsed_rows, grouped_days)
    whats_included = manual_whats_included or create_whats_included(parsed_rows, grouped_days)

    optional_addons = create_optional_addons(parsed_rows)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included(parsed_rows)

    important_travel_notes = get_important_travel_notes(output_edits)

    html_text = build_preview_style(colors, cover_theme, cover_background_data_uri)
    html_text += f"""    <div class="preview-background" data-preset="{esc(preset_name)}" data-colors="{colors_json}">

"""
    html_text += render_cover_page(
        cover_theme=cover_theme,
        cover_background_path=cover_background_path,
        cover_kicker=cover_kicker,
        cover_title_class=cover_title_class,
        trip_title=trip_title,
        trip_subtitle_html=trip_subtitle_html,
        trip_dates=trip_dates,
        destinations_line_html=destinations_line_html,
    )
    html_text += render_summary_page(
        cover_theme=cover_theme,
        trip_glance=trip_glance,
        journey_arc=journey_arc,
    )

    html_text += render_day_pages(_grouped_days_with_day_optional_rows(grouped_days, parsed_rows), output_edits)

    if output_edits.get("whats_included_pages_html"):
        html_text += render_custom_html_final_pages("What’s included", output_edits.get("whats_included_pages_html"), "final-list-page categorized-inclusions-page")
    elif output_edits.get("whats_included_html"):
        html_text += render_custom_html_final_page("What’s included", output_edits.get("whats_included_html"), "final-list-page categorized-inclusions-page")
    elif manual_whats_included:
        html_text += render_split_list_pages("What’s included", whats_included)
    else:
        html_text += render_categorized_inclusions_pages("What’s included", categorized_inclusions)
    html_text += render_optional_addons_pages(optional_addons)
    html_text += render_split_list_pages("What’s not included", whats_not_included)
    html_text += render_text_paragraph_page("Important travel notes", important_travel_notes)

    html_text += "</div>"

    return html_text
