"""Standalone transport row block builders."""

from __future__ import annotations

from itinerary_generation.common import get_row_type
from itinerary_generation.inclusions import clean_include_item
from text_polish import (
    format_duration_display,
    polish_inclusion_item,
    polish_inclusion_items,
    polish_title,
)
from ui.render_helpers import display_time, esc, normalize_list, render_list_items


def _is_cruise_leisure_row(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    return get_row_type(row) == "Cruise" and "leisure" in text and "cruise" in text


def build_transport_block(row, title_override=None):
    title = polish_title(title_override or row.get("title", ""))
    time = row.get("time", "")
    duration = row.get("duration", "")
    includes = polish_inclusion_items([clean_include_item(item, title) for item in normalize_list(row.get("includes", []))], title)
    luggage_included = polish_inclusion_item(clean_include_item(row.get("luggage_included", ""), title), title)

    html_text = f'<div class="content-block transport-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Travel Today</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if time:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(display_time(time))}</div>'

    if duration:
        clean_duration = format_duration_display(duration)
        html_text += f'<div class="body-text"><span class="meta-label">Duration:</span> {esc(clean_duration)}</div>'

    if luggage_included:
        html_text += f'<div class="body-text"><span class="meta-label">Luggage included:</span> {esc(luggage_included)}</div>'

    if includes:
        html_text += '<div class="section-title small-section">Includes</div>'
        html_text += render_list_items(includes)

    html_text += "</div>"

    return {
        "kind": "transport",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }

def build_self_transfer_block(row, title_override=None):
    title = polish_title(title_override or row.get("title", ""))
    city = polish_title(row.get("city", ""))

    html_text = f'<div class="content-block self-transfer-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Self Transfer</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if city:
        html_text += f'<div class="body-text"><span class="meta-label">Location:</span> {esc(city)}</div>'

    html_text += (
        '<div class="body-text muted-note">'
        'This is a self transfer, so please make your own way between these points. '
        'Transfer costs are not included unless specifically stated elsewhere in the itinerary.'
        '</div>'
    )
    html_text += "</div>"

    return {
        "kind": "self_transfer",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }

def build_self_arranged_travel_block(row, title_override=None):
    title = polish_title(title_override or row.get("title", ""))
    city = polish_title(row.get("city", ""))
    row_type = get_row_type(row).lower()

    if row_type == "flight" or "flight" in str(title).lower():
        note = "This flight is self-arranged and not included in the package price unless specifically stated."
    else:
        note = "This travel segment is self-arranged and not included in the package price unless specifically stated."

    html_text = f'<div class="content-block self-arranged-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Self-Arranged Travel</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if city:
        html_text += f'<div class="body-text"><span class="meta-label">Destination:</span> {esc(city)}</div>'

    html_text += f'<div class="body-text muted-note">{esc(note)}</div>'
    html_text += "</div>"

    return {
        "kind": "self_arranged_travel",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }

