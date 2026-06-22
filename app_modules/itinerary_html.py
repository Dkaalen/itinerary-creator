import json

from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.quality_gate import evaluate_client_output_quality
from app_modules.itinerary_html_sections import (
    balanced_cover_subtitle_html,
    render_cover_page,
    render_summary_page,
)
from app_modules.itinerary_html_styles import build_preview_style
from ui.day_pages import (
    render_day_pages,
    render_split_list_pages,
    render_categorized_inclusions_pages,
    render_custom_html_final_page,
    render_custom_html_final_pages,
    render_text_paragraph_page,
)
from ui.final_pages import render_optional_addons_pages
from ui.render_helpers import esc


def _balanced_cover_subtitle_html(subtitle: str) -> str:
    """Compatibility wrapper for tests/older imports."""
    return balanced_cover_subtitle_html(subtitle)


def _balanced_cover_destinations_html(destinations_line: str) -> str:
    """Compatibility wrapper for tests/older imports."""
    from itinerary_generation.cover_route import cover_route_html

    return cover_route_html(destinations_line)


def _raise_for_blocking_client_output(context) -> None:
    report = evaluate_client_output_quality(context.render_document)
    if report.is_blocked:
        details = "; ".join(
            f"{issue.code}: {issue.message}" for issue in report.blocking_issues
        )
        raise ValueError(f"Client output quality gate blocked itinerary generation: {details}")


def build_itinerary_html_from_context(context):
    """Render preview HTML from an already-built itinerary render context."""

    _raise_for_blocking_client_output(context)
    colors_json = esc(json.dumps(context.colors))

    html_text = build_preview_style(context.colors, context.cover_theme, context.cover_background_data_uri)
    html_text += f'''    <div class="preview-background" data-preset="{esc(context.preset_name)}" data-colors="{colors_json}">

'''
    html_text += render_cover_page(
        cover_theme=context.cover_theme,
        cover_background_path=context.cover_background_path,
        cover_crop_focus=context.cover_crop_focus,
        cover_kicker=context.cover_kicker,
        cover_title_class=context.cover_title_class,
        trip_title=context.trip_title,
        trip_subtitle_html=context.trip_subtitle_html,
        trip_dates=context.trip_dates,
        destinations_line_html=context.destinations_line_html,
    )
    html_text += render_summary_page(
        cover_theme=context.cover_theme,
        trip_glance=context.trip_glance,
        journey_arc=context.journey_arc,
        summary_background_data_uri=context.summary_background_data_uri,
        summary_background_path=context.summary_background_path,
        summary_crop_focus=context.summary_crop_focus,
    )

    html_text += render_day_pages(context.render_grouped_days, context.output_edits, render_document=context.render_document)

    if context.typed_inclusions_owned:
        if context.typed_inclusion_pages:
            html_text += render_custom_html_final_pages("What’s included", context.typed_inclusion_pages, "final-list-page categorized-inclusions-page")
    elif context.output_edits.get("whats_included_pages_html"):
        html_text += render_custom_html_final_pages("What’s included", context.output_edits.get("whats_included_pages_html"), "final-list-page categorized-inclusions-page")
    elif context.output_edits.get("whats_included_html"):
        html_text += render_custom_html_final_page("What’s included", context.output_edits.get("whats_included_html"), "final-list-page categorized-inclusions-page")
    elif context.manual_whats_included:
        html_text += render_split_list_pages("What’s included", context.whats_included)
    else:
        html_text += render_categorized_inclusions_pages("What’s included", context.categorized_inclusions)
    html_text += render_optional_addons_pages(context.optional_addons)
    if context.typed_exclusions_owned:
        if context.typed_exclusion_html:
            html_text += render_custom_html_final_page("What’s not included", context.typed_exclusion_html, "final-list-page categorized-exclusions-page")
    elif context.output_edits.get("whats_not_included_html"):
        html_text += render_custom_html_final_page("What’s not included", context.output_edits.get("whats_not_included_html"), "final-list-page categorized-exclusions-page")
    elif context.output_edits.get("whats_not_included_text"):
        html_text += render_split_list_pages("What’s not included", context.whats_not_included)
    else:
        html_text += render_categorized_inclusions_pages("What’s not included", context.structured_whats_not_included, "final-list-page categorized-exclusions-page")
    html_text += render_text_paragraph_page("Important travel notes", context.important_travel_notes)

    html_text += "</div>"

    return html_text


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    context = build_itinerary_render_context(parsed_rows, grouped_days, output_edits or {})
    return build_itinerary_html_from_context(context)
