import json

from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.quality_gate import evaluate_client_output_quality
from app_modules.itinerary_html_sections import (
    balanced_cover_subtitle_html,
    render_cover_page,
    render_summary_page,
)
from app_modules.itinerary_html_styles import build_preview_style
from ui.day_page_sections import render_day_page_html_by_id
from app_modules.render_final_sections_html import render_final_sections_html_by_id
from ui.render_helpers import esc
from itinerary_generation.editor_page_contract import ordered_page_ids, page_is_hidden as contract_page_is_hidden


def _balanced_cover_subtitle_html(subtitle: str) -> str:
    """Compatibility wrapper for tests/older imports."""
    return balanced_cover_subtitle_html(subtitle)


def _balanced_cover_destinations_html(destinations_line: str) -> str:
    """Compatibility wrapper for tests/older imports."""
    from itinerary_generation.cover_route import cover_route_html

    return cover_route_html(destinations_line)


def _raise_for_blocking_client_output(context) -> None:
    """Record late client-output gate failures without crashing preview generation.

    The sanitizer/quality gate still runs, but hosted generation should remain
    usable. Blocking details are added to render-document warnings so QA and
    editor surfaces can still show the problem. The legacy function name stays
    for compatibility with older imports/tests.
    """

    report = evaluate_client_output_quality(context.render_document)
    if not report.is_blocked:
        return
    details = "; ".join(
        f"{issue.code}: {issue.message}" for issue in report.blocking_issues
    )
    warning = f"Client output safety check warning: {details}"
    warnings = getattr(context.render_document, "warnings", None)
    if isinstance(warnings, list) and warning not in warnings:
        warnings.append(warning)


def _page_is_hidden(context, page_id: str) -> bool:
    return contract_page_is_hidden(getattr(context, "hidden_page_ids", set()) or set(), page_id)


def build_itinerary_html_from_context(context):
    """Render preview HTML from an already-built itinerary render context."""

    _raise_for_blocking_client_output(context)
    colors_json = esc(json.dumps(context.colors))

    html_text = build_preview_style(context.colors, context.cover_theme, context.cover_background_data_uri, output_brand=context.output_brand, brand_logo_data_uri=context.brand_logo_data_uri)
    html_text += f'''    <div class="preview-background" data-preset="{esc(context.preset_name)}" data-output-brand="{esc(context.output_brand)}" data-colors="{colors_json}">

'''
    page_html_by_id = {}
    if not _page_is_hidden(context, "cover"):
        page_html_by_id["cover"] = render_cover_page(
            cover_theme=context.cover_theme,
            cover_background_path=context.cover_background_path,
            cover_crop_focus=context.cover_crop_focus,
            cover_kicker=context.cover_kicker,
            cover_title_class=context.cover_title_class,
            trip_title=context.trip_title,
            trip_subtitle_html=context.trip_subtitle_html,
            trip_dates=context.trip_dates,
            destinations_line_html=context.destinations_line_html,
            route_label=context.cover_route_label,
        )
    if not _page_is_hidden(context, "summary"):
        page_html_by_id["summary"] = render_summary_page(
            cover_theme=context.cover_theme,
            trip_glance=context.trip_glance,
            journey_arc=context.journey_arc,
            trip_glance_title=context.trip_glance_title,
            journey_arc_title=context.journey_arc_title,
            journey_arc_columns=context.journey_arc_columns,
            summary_background_data_uri=context.summary_background_data_uri,
            summary_background_path=context.summary_background_path,
            summary_crop_focus=context.summary_crop_focus,
            output_brand=context.output_brand,
        )

    page_html_by_id.update(render_day_page_html_by_id(context.render_grouped_days, context.output_edits, render_document=context.render_document))
    page_html_by_id.update(render_final_sections_html_by_id(context.render_document.final_sections))

    for page_id in ordered_page_ids(list(page_html_by_id), getattr(context.render_document, "page_order", []) or []):
        html_text += page_html_by_id[page_id]

    html_text += "</div>"

    return html_text


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    context = build_itinerary_render_context(parsed_rows, grouped_days, output_edits or {})
    return build_itinerary_html_from_context(context)
