"""A4 day-page rendering helpers."""

from itinerary_generation.common import get_primary_city, get_row_type
from itinerary_generation.canonical_builder import canonical_day
from itinerary_generation.date_resolver import get_day_date_text
from images.app_image_selection import render_day_image_slot, select_day_images_with_overrides
from text_polish import polish_client_text
from ui.day_blocks import build_day_blocks
from ui.editor_sanitizer import clean_visual_editor_html
from ui.render_helpers import (
    esc,
    normalize_list,
    render_list_items,
    get_detail_level_name,
)


def render_day_section(day, rows, output_edits=None):
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    detail_level = get_detail_level_name(output_edits)
    canonical = canonical_day(day, rows, output_edits=output_edits, detail_level=detail_level)
    day_title = canonical.title
    day_intro = canonical.intro
    city = canonical.city
    blocks = build_day_blocks(rows)
    day_number = canonical.number
    day_date = get_day_date_text(rows)
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

    blocks_override = day_edits.get("blocks_html")
    if blocks_override:
        html_text += clean_visual_editor_html(blocks_override)
    else:
        for block in blocks:
            html_text += block["html"]

    html_text += "</section>"
    return html_text


def render_day_visual_block(day, rows, output_edits=None, image_match=None):
    """Render the matched day image with the premium edge divider handled by CSS/PDF."""
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
    image_matches = select_day_images_with_overrides(grouped_days, output_edits)
    for day, rows in grouped_days.items():
        html_text += render_day_page(day, rows, output_edits, image_match=image_matches.get(day))
    return html_text


def render_split_list_pages(title, items, items_per_page=24):
    html_text = ""
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    for start in range(0, len(clean_items), items_per_page):
        chunk = clean_items[start:start + items_per_page]
        continued = "" if start == 0 else " continued"

        html_text += f"""
        <div class="a4-page final-list-page">
            <div class="final-page-title">{esc(title)}{continued}</div>
            {render_list_items(chunk, class_name="final-list")}
        </div>
        """

    return html_text


def _render_inclusion_item(item, *, bullet_multiline=False):
    text = str(item or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    if "\n" not in text:
        return f"<li>{esc(text)}</li>"

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    if bullet_multiline:
        detail_html = "".join(
            f'<div class="inclusion-entry-detail">{esc(line)}</div>'
            for line in lines[1:]
        )
        return (
            '<ul class="detail-list inclusion-category-list inclusion-multiline-list">'
            f'<li><div class="strong-line inclusion-entry-title">{esc(lines[0])}</div>{detail_html}</li>'
            '</ul>'
        )

    html_text = f'<div class="body-text strong-line inclusion-entry-title">{esc(lines[0])}</div>'
    for line in lines[1:]:
        html_text += f'<div class="body-text inclusion-entry-detail">{esc(line)}</div>'
    return html_text


def render_inclusion_sections_inner_html(sections):
    clean_sections = []
    for section in sections or []:
        section_title = str(section.get("title", "")).strip()
        raw_items = section.get("items", []) or []
        items = [str(item or "").strip() for item in raw_items if str(item or "").strip()]
        if section_title and items:
            clean_sections.append({"title": section_title, "items": items})

    html_text = ""
    for section in clean_sections:
        html_text += '<div class="content-block inclusion-category-block">'
        html_text += f'<div class="section-title">{esc(section["title"])}</div>'

        plain_items = []
        multiline_count = 0
        bullet_multiline = section["title"].strip().lower() != "accommodation"
        for item in section["items"]:
            if "\n" in item:
                if plain_items:
                    html_text += render_list_items(plain_items, class_name="detail-list inclusion-category-list")
                    plain_items = []
                if multiline_count and not bullet_multiline:
                    html_text += '<div class="body-text inclusion-entry-spacer">&nbsp;</div>'
                html_text += _render_inclusion_item(item, bullet_multiline=bullet_multiline)
                multiline_count += 1
            else:
                plain_items.append(item)

        if plain_items:
            html_text += render_list_items(plain_items, class_name="detail-list inclusion-category-list")

        html_text += '</div>'
    return html_text


def _estimate_inclusion_item_units(item):
    text = str(item or "")
    lines = [line for line in text.split("\n") if line.strip()] or [text]
    units = 2 + max(0, len(lines) - 1)
    if len(text) > 90:
        units += 1
    if len(text) > 170:
        units += 1
    if len(text) > 260:
        units += 1
    return units


def _estimate_inclusion_section_units(section):
    """Approximate vertical space for keeping inclusion categories together.

    Categories are kept together whenever they can fit on an otherwise empty
    page. If one item would push a category over the current page limit, the
    whole category moves to the next page. Only categories that are too large to
    fit by themselves are split, with the heading repeated as ``continued``.
    """
    units = 4  # section title and spacing
    for item in section.get("items", []) or []:
        units += _estimate_inclusion_item_units(item)
    return units


def _split_oversized_inclusion_section(section, page_body_units):
    section_title = str(section.get("title", "")).strip()
    chunks = []
    current_items = []
    current_units = 4

    for item in section.get("items", []) or []:
        item_units = _estimate_inclusion_item_units(item)
        if current_items and current_units + item_units > page_body_units:
            chunks.append({"title": section_title if not chunks else f"{section_title} continued", "items": current_items})
            current_items = []
            current_units = 4
        current_items.append(item)
        current_units += item_units

    if current_items:
        chunks.append({"title": section_title if not chunks else f"{section_title} continued", "items": current_items})

    return chunks or [section]


def render_categorized_inclusions_pages(title, sections):
    clean_sections = []
    for section in sections or []:
        section_title = str(section.get("title", "")).strip()
        items = [str(item or "").strip() for item in (section.get("items", []) or []) if str(item or "").strip()]
        if section_title and items:
            clean_sections.append({"title": section_title, "items": items})

    if not clean_sections:
        return ""

    pages = []
    current = []
    current_units = 7  # final page title and top spacing
    max_units = 58
    empty_page_body_units = max_units - 7

    for section in clean_sections:
        candidate_sections = [section]
        if _estimate_inclusion_section_units(section) > empty_page_body_units:
            candidate_sections = _split_oversized_inclusion_section(section, empty_page_body_units)

        for candidate in candidate_sections:
            section_units = _estimate_inclusion_section_units(candidate)
            if current and current_units + section_units > max_units:
                pages.append(current)
                current = []
                current_units = 7
            current.append(candidate)
            current_units += section_units

    if current:
        pages.append(current)

    html_text = ""
    for index, page_sections in enumerate(pages):
        continued = "" if index == 0 else " continued"
        inner_html = render_inclusion_sections_inner_html(page_sections)
        html_text += f'<div class="a4-page final-list-page categorized-inclusions-page"><div class="final-page-title">{esc(title)}{continued}</div>{inner_html}</div>'
    return html_text


def render_custom_html_final_page(title, inner_html, page_class="final-list-page"):
    inner_html = clean_visual_editor_html(inner_html or "")
    if not inner_html:
        return ""
    return f'<div class="a4-page {esc(page_class)}"><div class="final-page-title">{esc(title)}</div>{inner_html}</div>'


def render_text_paragraph_page(title, paragraphs):
    clean_paragraphs = [polish_client_text(item) for item in normalize_list(paragraphs) if polish_client_text(item)]
    if not clean_paragraphs:
        return ""

    html_text = (
        f'<div class="a4-page final-list-page important-notes-page">'
        f'<div class="final-page-title">{esc(title)}</div>'
        f'<div class="content-block notes-block">'
    )
    for paragraph in clean_paragraphs:
        html_text += f'<div class="body-text note-paragraph">{esc(paragraph)}</div>'
    html_text += "</div></div>"
    return html_text
