"""A4 itinerary day page rendering."""

from __future__ import annotations

from itinerary_generation.common import is_optional_row
from itinerary_generation.day_render_blocks import build_render_day
from itinerary_generation.date_resolver import get_day_date_text
from itinerary_generation.editable_draft import day_by_id
from itinerary_generation.generated_ownership import resolve_blocks_html
from images.app_image_selection import render_day_image_slot, select_day_images_with_overrides
from ui.render_blocks import render_blocks_to_html
from ui.editor_sanitizer import clean_visual_editor_html
from ui.render_helpers import esc, get_detail_level_name
from ui.picture_workflow import pictures_are_added


def render_day_section(day, rows, output_edits=None, render_day=None):
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    typed_day = day_by_id((output_edits or {}).get("editor_draft", {}) if isinstance(output_edits, dict) else {}, day)
    if render_day is None:
        detail_level = get_detail_level_name(output_edits)
        render_day = build_render_day(day, rows, output_edits=output_edits, detail_level=detail_level)
    main_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
    day_title = render_day.title
    day_intro = render_day.intro
    city = render_day.city
    blocks = render_day.blocks
    day_number = render_day.number
    day_date = get_day_date_text(main_rows)
    day_kicker_html = f"DAY {esc(day_number)}"
    if city:
        day_kicker_html += f' <span class="day-kicker-symbol">✦</span> {esc(str(city).upper())}'
    if day_date:
        day_kicker_html += f' <span class="day-kicker-symbol">✦</span> {esc(day_date)}'
    html_text = f'''
            <section class="day-section" data-day="{esc(day)}">
                <div class="day-kicker">{day_kicker_html}</div>
                <div class="day-label day-label-legacy">{esc(day)}</div>
                <div class="day-title">{esc(day_title)}</div>
                <div class="city">{esc(city)}</div>
                <div class="intro">{esc(day_intro)}</div>
    '''

    generated_blocks_html = render_blocks_to_html(blocks)
    resolved_blocks = resolve_blocks_html(
        day_edits=day_edits if isinstance(day_edits, dict) else {},
        typed_day=typed_day if isinstance(typed_day, dict) else {},
        generated_blocks_html=generated_blocks_html,
    )
    html_text += clean_visual_editor_html(resolved_blocks.html)

    html_text += "</section>"
    return html_text


def render_day_visual_block(day, rows, output_edits=None, image_match=None):
    """Render the matched day image with the edge divider handled by CSS/PDF."""
    if not image_match:
        return ""

    image_slot = render_day_image_slot(day, rows, match=image_match, output_edits=output_edits)
    if not image_slot:
        return ""

    return f"""
            <div class="day-visual-block">
                {image_slot}
            </div>
    """


def render_day_page(day, rows, output_edits=None, image_match=None, render_day=None):
    return f'''
        <div class="a4-page day-page single-day-page" data-day="{esc(day)}">
            {render_day_section(day, rows, output_edits, render_day=render_day)}
            {render_day_visual_block(day, rows, output_edits=output_edits, image_match=image_match)}
        </div>
    '''


def render_day_pages(grouped_days, output_edits=None, render_document=None):
    """Render exactly one itinerary day per A4 page.

    v36 image placement depends on predictable one-day pages so the PDF exporter
    can place a full-width image below the day text when enough space remains.
    """
    html_text = ""
    if pictures_are_added(output_edits):
        image_grouped_days = {day: [row for row in rows if not is_optional_row(row)] or list(rows) for day, rows in grouped_days.items()}
        image_matches = select_day_images_with_overrides(image_grouped_days, output_edits)
    else:
        image_matches = {}
    render_days_by_day = {str(render_day.day): render_day for render_day in getattr(render_document, "days", []) or []}
    for day, rows in grouped_days.items():
        html_text += render_day_page(
            day,
            rows,
            output_edits,
            image_match=image_matches.get(day),
            render_day=render_days_by_day.get(str(day)),
        )
    return html_text


