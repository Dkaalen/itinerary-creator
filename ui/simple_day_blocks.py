"""Small, static day block renderers used by ui.day_blocks."""

from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.title_safety import is_forbidden_client_title
from text_polish import polish_inclusion_items, polish_title
from ui.render_helpers import esc, normalize_list, render_list_items


def build_leisure_block(row=None):
    row_id = row.get("row_id", "") if row else ""

    html_text = f'<div class="content-block leisure-block" data-row-id="{esc(row_id)}">'
    html_text += '<div class="section-title">Your Free Time</div>'
    html_text += (
        '<div class="body-text">'
        'Enjoy the remaining time at your own pace, whether you prefer a relaxed meal, '
        'a quiet walk nearby or simply settling into the destination.'
        '</div>'
    )
    html_text += "</div>"

    return {
        "kind": "leisure",
        "row_id": row_id,
        "html": html_text,
    }


def build_cruise_leisure_block(row):
    html_text = f'<div class="content-block cruise-leisure-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Onboard leisure</div>'
    html_text += '<div class="body-text strong-line">Spend time at leisure onboard the cruise</div>'
    html_text += (
        '<div class="body-text">'
        'Enjoy a relaxed day onboard the cruise, with time to take in the coastal scenery, '
        'use the ship facilities and settle into the rhythm of the voyage.'
        '</div>'
    )
    html_text += "</div>"
    return {"kind": "cruise_leisure", "row_id": row.get("row_id", ""), "html": html_text}


def build_arrival_block(row):
    city = polish_title(row.get("city", ""))
    title = clean_client_title(row.get("title", ""), row)
    if is_forbidden_client_title(title) or not title or title.lower().strip(" .") in {"arrival", "arrival day", "welcome", "welcome day"}:
        title = f"Arrival in {city}" if city else "Arrival"

    html_text = f'<div class="content-block arrival-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Arrival</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'
    html_text += "</div>"

    return {
        "kind": "arrival",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


def build_departure_block(row):
    title = clean_client_title(row.get("title", "") or "", row)
    if is_forbidden_client_title(title) or not title or title.lower().strip(" .") in {"departure", "departure day"}:
        title = "Journey home"

    html_text = f'<div class="content-block departure-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Departure</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'
    html_text += '</div>'

    return {
        "kind": "departure",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


def build_included_today_block(items):
    clean_items = polish_inclusion_items(normalize_list(items))

    if not clean_items:
        return None

    html_text = '<div class="content-block included-block">'
    html_text += '<div class="section-title">Included Today</div>'
    html_text += render_list_items(clean_items)
    html_text += "</div>"

    return {
        "kind": "included",
        "row_id": "included-today",
        "html": html_text,
    }
