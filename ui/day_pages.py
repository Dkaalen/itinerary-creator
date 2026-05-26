"""A4 day-page rendering and packing helpers."""

import re

from generator import create_day_intro, create_day_title, get_primary_city, get_row_type
from layout_policy import (
    is_day_packing_enabled,
    is_three_day_packing_enabled as policy_is_three_day_packing_enabled,
)
from images.app_image_selection import render_day_image_slot, select_day_images_with_overrides
from text_polish import polish_client_text
from ui.day_blocks import build_day_blocks
from ui.editor_sanitizer import clean_visual_editor_html
from ui.render_helpers import (
    esc,
    normalize_list,
    render_list_items,
    get_day_page_layout_name,
    get_detail_level_name,
    is_smart_day_packing_enabled,
    is_three_day_packing_enabled,
)


def estimate_day_units(day, rows, output_edits=None):
    """Estimate vertical space for a day section.

    This is a general, content-based estimate used by the smart A4 packing
    system. It intentionally scores the generated day blocks rather than day
    numbers or destination names, so the same logic works for every itinerary.
    """

    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    detail_level = get_detail_level_name(output_edits)
    day_title = day_edits.get("title") or create_day_title(rows)
    day_intro = day_edits.get("intro") or create_day_intro(rows, detail_level=detail_level)
    city = day_edits.get("city") or get_primary_city(rows)
    blocks = build_day_blocks(rows)

    # Header + city + intro. The base is intentionally lower than the old
    # estimator because packed pages use tighter spacing but should not look
    # like a different font system.
    units = 4.6
    units += max(0, (len(str(day_title)) - 48) / 70)
    units += max(0, (len(str(day_intro)) - 155) / 145)
    if city:
        units += 0.35

    for block in blocks:
        kind = block.get("kind", "")
        html_text = block.get("html", "")
        text_only = re.sub(r"<[^>]+>", " ", html_text)
        text_length = len(" ".join(text_only.split()))

        if kind == "included":
            bullet_count = html_text.count("<li>")
            units += 1.55 + bullet_count * 0.55 + max(0, (text_length - 120) / 220)
        elif kind == "activity":
            units += 3.05 + max(0, (text_length - 210) / 185)
        elif kind == "transport":
            units += 2.85 + max(0, (text_length - 185) / 190)
        elif kind in {"self_transfer", "self_arranged_travel"}:
            units += 3.05 + max(0, (text_length - 190) / 210)
        elif kind == "accommodation":
            units += 2.55 + max(0, (text_length - 155) / 220)
        elif kind == "leisure":
            units += 2.5
        else:
            units += 2.45 + max(0, text_length / 240)

    units += max(0, len(rows) - 4) * 0.35
    return units


def get_day_pack_stats(day, rows, output_edits=None):
    blocks = build_day_blocks(rows)
    return {
        "units": estimate_day_units(day, rows, output_edits),
        "activity_count": sum(1 for row in rows if get_row_type(row) == "Activity"),
        "block_count": len(blocks),
        "row_count": len(rows),
        "has_long_description": any(len(str(row.get("client_description", "") or row.get("details", ""))) > 420 for row in rows),
    }


def can_pack_days(day_a, rows_a, day_b, rows_b, output_edits=None):
    if not is_smart_day_packing_enabled(output_edits):
        return False

    a = get_day_pack_stats(day_a, rows_a, output_edits)
    b = get_day_pack_stats(day_b, rows_b, output_edits)

    # Packed pages now use the same visual typography as single-day pages.
    # Only combine genuinely light days; split instead of shrinking font sizes.
    if a["units"] > 18.5 or b["units"] > 18.5:
        return False
    if a["units"] + b["units"] > 30.5:
        return False
    if a["units"] > 15.5 and b["units"] > 15.5:
        return False
    if a["activity_count"] >= 3 or b["activity_count"] >= 3:
        return False
    if a["activity_count"] >= 2 and b["activity_count"] >= 2:
        return False
    if a["block_count"] >= 7 or b["block_count"] >= 7:
        return False

    return True


def can_pack_three_days(day_rows_triple, output_edits=None):
    """Allow three consecutive days on one A4 page in explicit 3-day mode.

    This is not tailored to any specific day. It uses the same content-density
    rules for all itineraries: short headers, limited blocks, modest text, and a
    safe combined A4 height estimate.
    """

    if not is_three_day_packing_enabled(output_edits):
        return False

    if len(day_rows_triple) != 3:
        return False

    stats = [get_day_pack_stats(day, rows, output_edits) for day, rows in day_rows_triple]
    total_units = sum(item["units"] for item in stats)
    activity_total = sum(item["activity_count"] for item in stats)
    block_total = sum(item["block_count"] for item in stats)

    # A4 safety guardrails. The total limit is what matters most; individual
    # medium-light days are allowed as long as the combined page remains safe.
    if total_units > 58.5:
        return False
    if any(item["units"] > 24.5 for item in stats):
        return False
    if any(item["block_count"] > 7 for item in stats):
        return False
    if block_total > 16:
        return False
    if activity_total > 4:
        return False
    if any(item["activity_count"] > 2 for item in stats):
        return False
    if any(item["has_long_description"] and item["units"] > 19.5 for item in stats):
        return False

    return True


def render_day_section(day, rows, output_edits=None, packed=False, triple=False):
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    day_title = day_edits.get("title") or create_day_title(rows)
    detail_level = get_detail_level_name(output_edits)
    day_intro = day_edits.get("intro") or create_day_intro(rows, detail_level=detail_level)
    city = day_edits.get("city") or get_primary_city(rows)
    blocks = build_day_blocks(rows)
    section_class = "day-section"
    if packed:
        section_class += " packed-section"
    if triple:
        section_class += " triple-packed-section"

    html_text = f'''
            <section class="{section_class}" data-day="{esc(day)}">
                <div class="day-label">{esc(day)}</div>
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


def render_day_page(day, rows, output_edits=None, image_match=None):
    return f'''
        <div class="a4-page day-page single-day-page" data-day="{esc(day)}">
            {render_day_section(day, rows, output_edits, packed=False)}
            {render_day_image_slot(day, rows, match=image_match, output_edits=output_edits)}
        </div>
    '''


def render_packed_day_page(day_rows_pairs, output_edits=None):
    day_values = "|".join(day for day, _ in day_rows_pairs)
    triple = len(day_rows_pairs) == 3
    page_class = "a4-page day-page packed-day-page" + (" triple-day-page" if triple else "")
    html_text = f'''
        <div class="{page_class}" data-days="{esc(day_values)}">
    '''

    for index, (day, rows) in enumerate(day_rows_pairs):
        if index > 0:
            html_text += '<div class="day-separator"></div>'
        html_text += render_day_section(day, rows, output_edits, packed=True, triple=triple)

    html_text += "</div>"
    return html_text


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
