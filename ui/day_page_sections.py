"""A4 itinerary day page rendering."""

from __future__ import annotations

from itinerary_generation.canonical_builder import canonical_day
from itinerary_generation.common import is_optional_row
from itinerary_generation.date_resolver import get_day_date_text
from images.app_image_selection import render_day_image_slot, select_day_images_with_overrides
from ui.day_blocks import build_day_blocks
from ui.editor_sanitizer import clean_visual_editor_html
from ui.render_helpers import esc, get_detail_level_name


def render_day_section(day, rows, output_edits=None):
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    detail_level = get_detail_level_name(output_edits)
    main_rows = [row for row in rows if not is_optional_row(row)] or list(rows)
    canonical = canonical_day(day, main_rows, output_edits=output_edits, detail_level=detail_level)
    day_title = canonical.title
    day_intro = canonical.intro
    city = canonical.city
    blocks = build_day_blocks(rows)
    day_number = canonical.number
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

    if "blocks_html" in day_edits:
        # Presence matters here: an empty saved editor block means the user
        # intentionally cleared the generated content for this day.
        html_text += clean_visual_editor_html(day_edits.get("blocks_html", ""))
    else:
        for block in blocks:
            html_text += block["html"]

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


def render_day_page(day, rows, output_edits=None, image_match=None):
    return f'''
        <div class="a4-page day-page single-day-page" data-day="{esc(day)}">
            {render_day_section(day, rows, output_edits)}
            {render_day_visual_block(day, rows, output_edits=output_edits, image_match=image_match)}
        </div>
    '''


def render_day_pages(grouped_days, output_edits=None):
    """Render exactly one itinerary day per A4 page.

    v36 image placement depends on predictable one-day pages so the PDF exporter
    can place a full-width image below the day text when enough space remains.
    """
    html_text = ""
    image_grouped_days = {day: [row for row in rows if not is_optional_row(row)] or list(rows) for day, rows in grouped_days.items()}
    image_matches = select_day_images_with_overrides(image_grouped_days, output_edits)
    for day, rows in grouped_days.items():
        html_text += render_day_page(day, rows, output_edits, image_match=image_matches.get(day))
    return html_text


