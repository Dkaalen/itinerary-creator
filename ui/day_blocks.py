"""Day block builders for itinerary HTML/UI output."""

import re

from generator import (
    TRANSPORT_TYPES,
    clean_include_item,
    create_client_activity_title,
    get_primary_city,
    get_row_type,
    get_transfer_travel_title,
    is_route_transfer,
    is_self_arranged,
)
from text_polish import (
    format_duration_display,
    polish_client_text,
    polish_hotel_name,
    polish_inclusion_item,
    polish_inclusion_items,
    polish_title,
)
from ui.final_pages import (
    clean_activity_inclusion_items,
    get_fallback_activity_inclusions,
    prioritize_inline_inclusions,
)
from ui.render_helpers import (
    clean_space,
    display_time,
    display_time_with_duration,
    esc,
    get_activity_description,
    get_activity_duration_label,
    get_activity_logistics,
    get_detail_level_name,
    get_time_period,
    is_self_arranged_transport,
    is_self_transfer,
    is_tallinn_ferry_day_trip,
    meal_phrase,
    normalize_list,
    plural_nights,
    render_list_items,
)


def build_activity_block(row):
    title = polish_title(row.get("title", ""))
    time = row.get("display_time") or row.get("time", "")
    duration = row.get("display_duration") or polish_client_text(row.get("duration", ""))
    meeting_label, meeting_point = get_activity_logistics(row)
    meeting_point = polish_client_text(meeting_point)
    end_point = polish_client_text(row.get("end_point", ""))
    notable_sights = polish_inclusion_items(normalize_list(row.get("notable_sights", [])), title)
    description = polish_client_text(row.get("client_description") or get_activity_description(row))
    included_items = clean_activity_inclusion_items(row.get("includes", []), title)
    fallback_items = get_fallback_activity_inclusions(row)

    if not included_items:
        included_items = fallback_items
    elif title == "Day Trip to Tallinn" and fallback_items:
        for item in fallback_items:
            if item not in included_items:
                included_items.append(item)
        if "Guided experience" in included_items and len(included_items) > 1:
            included_items = [item for item in included_items if item != "Guided experience"]

    included_items = polish_inclusion_items(included_items, title)

    html_text = f'<div class="content-block activity-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += f'<div class="section-title">{esc(get_time_period(time))}</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    time_display = time if row.get("display_time") else display_time_with_duration(time, duration)
    if time_display:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(time_display)}</div>'

    if duration:
        duration_label = get_activity_duration_label(row, duration)
        clean_duration = format_duration_display(duration)
        html_text += f'<div class="body-text"><span class="meta-label">{esc(duration_label)}:</span> {esc(clean_duration)}</div>'

    if meeting_point:
        html_text += f'<div class="body-text"><span class="meta-label">{esc(meeting_label)}:</span> {esc(meeting_point)}</div>'

    if included_items:
        html_text += '<div class="section-title small-section">Included With This Experience</div>'
        html_text += render_list_items(prioritize_inline_inclusions(included_items, max_items=5))

    if end_point:
        html_text += f'<div class="body-text"><span class="meta-label">End point:</span> {esc(end_point)}</div>'

    if description:
        html_text += '<div class="section-title small-section">Description</div>'
        html_text += f'<div class="body-text muted-note">{esc(description)}</div>'

    if notable_sights:
        html_text += '<div class="section-title small-section">Notable Sights</div>'
        html_text += render_list_items(notable_sights)

    html_text += "</div>"

    return {
        "kind": "activity",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


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
    html_text += '<div class="section-title">Self-Guided Transfer</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if city:
        html_text += f'<div class="body-text"><span class="meta-label">Location:</span> {esc(city)}</div>'

    html_text += (
        '<div class="body-text muted-note">'
        'This is a self-guided transfer, so please make your own way between these points. '
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


def build_accommodation_block(row):
    hotel_name = polish_hotel_name(row.get("hotel_name") or row.get("title") or "Accommodation as listed")
    nights = plural_nights(row.get("hotel_nights", ""))
    room_category = polish_client_text(row.get("room_category") or "")
    meal = meal_phrase(row.get("meal_plan", ""))

    accommodation_line = polish_client_text(f"{hotel_name} or similar")

    if nights:
        accommodation_line += f" for {nights}"

    room_line_parts = []

    if room_category:
        room_line_parts.append(f"Room category: {room_category}")

    if meal:
        if room_line_parts:
            room_line_parts[-1] += f", {meal}"
        else:
            room_line_parts.append(meal.capitalize())

    html_text = f'<div class="content-block accommodation-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Accommodation</div>'
    html_text += f'<div class="body-text strong-line">{esc(accommodation_line)}</div>'

    for line in room_line_parts:
        html_text += f'<div class="body-text">{esc(line)}</div>'

    html_text += "</div>"

    return {
        "kind": "accommodation",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


def build_leisure_block(row=None):
    row_id = row.get("row_id", "") if row else ""

    html_text = f'<div class="content-block leisure-block" data-row-id="{esc(row_id)}">'
    html_text += '<div class="section-title">Your Free Time</div>'
    html_text += (
        '<div class="body-text">'
        'Time at leisure is included so the day does not feel overfilled. '
        'Use this space to settle in, explore nearby streets, enjoy a relaxed meal, '
        'or simply take the destination at your own pace.'
        '</div>'
    )
    html_text += "</div>"

    return {
        "kind": "leisure",
        "row_id": row_id,
        "html": html_text,
    }


def build_arrival_block(row):
    city = polish_title(row.get("city", ""))
    title = polish_title(row.get("title", ""))
    if not title or title.lower().strip(" .") in {"arrival", "arrival day", "welcome", "welcome day"}:
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
    title = polish_title(row.get("title", "") or "")
    if not title or title.lower().strip(" .") in {"departure", "departure day"}:
        title = "Onward travel arrangements"

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


def is_travel_sequence_candidate(row):
    """Rows that form chronological travel arrangements within a day."""

    row_type = get_row_type(row)
    return row_type == "Transfer" or row_type in TRANSPORT_TYPES


def get_travel_sequence_line(row):
    row_type = get_row_type(row)

    if row_type == "Transfer" and is_self_arranged(row):
        title = polish_title(get_transfer_travel_title(row) or row.get("title", "Self-arranged travel"))
        return f"{title} (self-arranged, not included)"

    if row_type in TRANSPORT_TYPES and is_self_arranged(row):
        title = polish_title(row.get("title", "Self-arranged travel"))
        if row_type == "Flight" and title.lower().startswith("flight"):
            return f"Self-arranged {title[0].lower() + title[1:]} (not included)"
        return f"{title} (self-arranged, not included)"

    if row_type == "Transfer" and is_route_transfer(row):
        return polish_title(get_transfer_travel_title(row) or row.get("title", ""))

    if row_type == "Transfer":
        return polish_title(row.get("title", ""))

    if row_type in TRANSPORT_TYPES:
        return polish_title(row.get("title", ""))

    return polish_title(row.get("title", ""))


def get_travel_arrangement_line(row):
    title = get_travel_sequence_line(row)
    time = display_time(row.get("time", ""))
    duration = polish_client_text(row.get("duration", ""))
    details = []

    if time:
        details.append(time)
    if duration and " - " not in time:
        clean_duration = format_duration_display(duration)
        if clean_duration:
            details.append(clean_duration)

    return f"{title} — {'; '.join(details)}" if details else title


def build_travel_arrangements_block(travel_rows):
    items = []
    for row in travel_rows:
        line = get_travel_arrangement_line(row)
        if line and line not in items:
            items.append(line)

    items = polish_inclusion_items(items)
    if not items:
        return None

    html_text = '<div class="content-block travel-sequence-block">'
    html_text += '<div class="section-title">Travel Arrangements</div>'
    html_text += render_list_items(items)
    html_text += "</div>"

    return {
        "kind": "travel_sequence",
        "row_id": "travel-arrangements",
        "html": html_text,
    }


def build_day_blocks(rows):
    """Build day content in source order, grouping only consecutive travel rows.

    This prevents later/overnight travel from being pulled above daytime
    activities, while still keeping transfer + flight/train + transfer chains
    tidy and easy to read.
    """

    blocks = []
    travel_group = []

    def flush_travel_group():
        nonlocal travel_group
        if travel_group:
            block = build_travel_arrangements_block(travel_group)
            if block:
                blocks.append(block)
            travel_group = []

    for row in rows:
        row_type = get_row_type(row)
        title = row.get("title", "")

        if is_travel_sequence_candidate(row):
            travel_group.append(row)
            continue

        flush_travel_group()

        if row_type == "Departure":
            blocks.append(build_departure_block(row))
        elif row_type == "Hotel":
            blocks.append(build_accommodation_block(row))
        elif row_type == "Arrival":
            blocks.append(build_arrival_block(row))
        elif row_type == "Activity":
            blocks.append(build_activity_block(row))
        elif row_type == "Leisure":
            blocks.append(build_leisure_block(row))
        elif title:
            included_block = build_included_today_block([polish_title(title)])
            if included_block:
                blocks.append(included_block)

    flush_travel_group()
    return blocks
