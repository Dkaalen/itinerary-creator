"""Day block builders for itinerary HTML/UI output."""

import re

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_primary_city,
    get_row_type,
    is_self_arranged,
)
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.titles import create_client_activity_title
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer, get_premium_transport_phrase
from text_polish import (
    strip_price_fragments,
    format_duration_display,
    polish_client_text,
    polish_hotel_name,
    polish_inclusion_item,
    polish_inclusion_items,
    polish_title,
)
from parser_modules.common import extract_route_points
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


def _preserve_common_acronyms(text):
    replacements = {
        "Atv": "ATV", "Atvs": "ATVs", "Suv": "SUV", "Suvs": "SUVs",
        "Spa": "SPA", "Vat": "VAT", "Wifi": "WiFi", "Wi-fi": "Wi-Fi",
        "Dc3": "DC3", "Bbq": "BBQ",
    }
    result = str(text or "")
    for source, target in replacements.items():
        result = re.sub(rf"\b{re.escape(source)}\b", target, result)
    return result


def _client_title_case_fragment(value):
    text = clean_space(str(value or ""))
    if not text:
        return ""
    return _preserve_common_acronyms(polish_title(text))



def build_activity_block(row):
    title = polish_title(create_client_activity_title(row) or row.get("title", ""))
    time = row.get("display_time") or row.get("time", "")
    duration = row.get("display_duration") or polish_client_text(row.get("duration", ""))
    meeting_label, meeting_point = get_activity_logistics(row)
    meeting_point = polish_client_text(meeting_point)
    end_point = polish_client_text(row.get("end_point", ""))
    notable_sights = polish_inclusion_items(normalize_list(row.get("notable_sights", [])), title)
    description = polish_client_text(row.get("client_description") or get_activity_description(row))
    included_items = clean_activity_inclusion_items([strip_price_fragments(item) for item in row.get("includes", [])], title)
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


def _is_cruise_leisure_row(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    return get_row_type(row) == "Cruise" and "leisure" in text and "cruise" in text


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


def _transport_route_phrase(row):
    return get_premium_transport_phrase(row)


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



def _polish_overview_item(value):
    item = clean_space(str(value or "")).strip(" •-*|:")
    if not item:
        return ""
    item = re.sub(r"\bPickupo\b", "Pick-up", item, flags=re.IGNORECASE)
    item = re.sub(r"\bPick\s+Up\b", "Pick-up", item, flags=re.IGNORECASE)
    item = re.sub(r"\bOtpions\b", "Options", item, flags=re.IGNORECASE)
    item = re.sub(r"\binlcuded\b", "included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bBrekafast\b", "Breakfast", item, flags=re.IGNORECASE)
    item = item.replace("/", " / ")
    item = re.sub(r"\s+", " ", item).strip()

    item = _client_title_case_fragment(item)

    # Keep a few destination/place spellings client-facing.
    item = re.sub(r"\bReykjavik\b", "Reykjavík", item)
    item = re.sub(r"\bKeflavik\b", "Keflavík", item)
    item = re.sub(r"\bVik\b", "Vík", item)
    item = re.sub(r"\bGothernburg\b", "Gothenburg", item, flags=re.IGNORECASE)
    item = re.sub(r"\bSvolaver\b", "Svolvær", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTrosmø\b", "Tromsø", item, flags=re.IGNORECASE)
    item = re.sub(r"\bKerid\b", "Kerið", item)
    # Avoid title-casing small prepositions introduced by supplier shorthand.
    item = re.sub(r"\bTo\b", "to", item)
    item = re.sub(r"\bFrom\b", "from", item)
    item = re.sub(r"\bAnd\b", "and", item)
    item = re.sub(r"\bScenic Return Drive to\b", "Scenic return drive to", item)
    item = re.sub(r"\bLuxury Stay\b", "Overnight near Glacier Lagoon", item)
    item = re.sub(r"\bDiamond Beach\b", "Diamond Beach area", item)
    return polish_title(item)


def _split_day_overview_items(text):
    source = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    source = re.sub(r"\bRoute\s+Suggested\b", "", source, flags=re.IGNORECASE)
    source = source.replace("✅", "")
    items = []
    optional = []
    in_optional = False

    # Preserve real supplier bullet lines first.
    for raw_line in source.splitlines() if "\n" in source else re.split(r"\s*\|\s*", source):
        line = clean_space(raw_line).strip(" •-*|:")
        if not line:
            continue
        if line.lower().startswith("optional"):
            in_optional = True
            remainder = clean_space(re.sub(r"^optional\s*:?", "", line, flags=re.IGNORECASE))
            if remainder:
                line = remainder
            else:
                continue
        # Split compact route shorthand like "GOLDEN CIRCLE + SILFRA + KERIÐ".
        parts = [clean_space(part).strip(" •-*") for part in re.split(r"\s+\+\s+", line) if clean_space(part).strip(" •-*")]
        target = optional if in_optional else items
        for part in parts:
            part = _polish_overview_item(part)
            if part and part not in target:
                target.append(part)

    return items, optional


def _is_rental_overview(text):
    lower = str(text or "").lower()
    return any(marker in lower for marker in ["rental vehicle", "rental car", "rental suv", "pick up rental", "pickup rental", "drop vehicle"])


def _build_rental_overview_block(row):
    text = str(row.get("details") or row.get("title") or "")
    lines = []
    for raw in text.replace("|", "\n").replace("✅", "").splitlines():
        line = _polish_overview_item(raw)
        if line:
            lines.append(line)

    pickup_lines = []
    examples = []
    included = []
    not_included = []
    mode = "pickup"
    for line in lines:
        lower = line.lower().strip(" :")
        if lower in {"included", "includes"}:
            mode = "included"
            continue
        if lower.startswith("not included"):
            mode = "not_included"
            remainder = clean_space(re.sub(r"^not included\s*: ?", "", line, flags=re.IGNORECASE))
            if remainder:
                not_included.append(remainder)
            continue
        if "option" in lower and "similar category" in lower:
            mode = "examples"
            continue
        if mode == "included":
            included.append(line)
        elif mode == "not_included":
            not_included.append(line)
        elif mode == "examples":
            examples.append(line)
        else:
            pickup_lines.append(line)

    is_dropoff = any("drop vehicle" in line.lower() or "return vehicle" in line.lower() for line in pickup_lines)
    vehicle_type = "rental SUV" if any("suv" in line.lower() for line in pickup_lines + examples) else "rental vehicle"
    first_example = examples[0] if examples else ""

    html_text = f'<div class="content-block day-overview-block rental-overview-block" data-row-id="{esc(row.get("row_id", ""))}">'

    if is_dropoff:
        html_text += '<div class="section-title">Travel Arrangements</div>'
        html_text += render_list_items(["Return your rental vehicle at the rental office or airport."])
        html_text += "</div>"
        return {"kind": "day_overview", "row_id": row.get("row_id", ""), "html": html_text}

    pickup_sentence = f"Pick up your {vehicle_type}"
    if first_example:
        pickup_sentence += f", such as a {first_example} or similar"
    else:
        pickup_sentence += " or similar"
    pickup_sentence += ", from the rental office or airport."

    included_clean = []
    for item in included:
        low = item.lower()
        if low == "automatic":
            item = "automatic transmission"
        included_clean.append(item)
    if included_clean:
        included_sentence = _join_rental_items(included_clean).capitalize() + " included."
    else:
        included_sentence = "Rental details as listed in the itinerary."

    html_text += '<div class="section-title">Rental vehicle</div>'
    html_text += render_list_items([pickup_sentence, included_sentence])
    if not_included:
        html_text += '<div class="section-title small-section">Not included</div>'
        html_text += render_list_items(not_included[:3])
    html_text += "</div>"
    return {"kind": "day_overview", "row_id": row.get("row_id", ""), "html": html_text}


def _join_rental_items(items):
    clean = [str(item).strip(" .") for item in items if str(item).strip(" .")]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + f" and {clean[-1]}"


def build_day_overview_block(row):
    text = row.get("details") or row.get("title", "")
    if _is_rental_overview(text):
        return _build_rental_overview_block(row)

    items, optional = _split_day_overview_items(text)
    lower = str(text or "").lower()
    explore_like = bool(re.search(r"(^|[\n|])\s*explore\b", str(text or ""), flags=re.IGNORECASE))
    route_like = any(marker in lower for marker in ["route", "drive", "waterfalls", "scenic", "return drive"])
    if explore_like:
        section = "Explore at your own pace"
        items = [item for item in items if item.lower() != "explore"]
    elif "return drive" in lower or "scenic drive" in lower:
        section = "Today’s route"
    elif route_like:
        section = "Suggested Route"
    else:
        section = "Included Today"
    html_text = f'<div class="content-block day-overview-block" data-row-id="{esc(row.get("row_id", ""))}">' 
    if items:
        html_text += f'<div class="section-title">{esc(section)}</div>'
        html_text += render_list_items(items)
    if optional:
        html_text += '<div class="section-title small-section">Optional ideas</div>'
        html_text += render_list_items(optional)
    html_text += "</div>"
    if not items and not optional:
        return None
    return {"kind": "day_overview", "row_id": row.get("row_id", ""), "html": html_text}

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
    if _is_cruise_leisure_row(row):
        return False
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
        phrase = get_premium_transport_phrase(row)
        return polish_title(phrase or row.get("title", ""))

    return polish_title(row.get("title", ""))


def _extract_timed_route_places(row):
    text = str(row.get("details") or row.get("original_title") or row.get("title") or "")
    places = []
    for raw in text.replace("|", "\n").splitlines():
        line = clean_space(raw)
        if not re.match(r"^\d{1,2}:\d{2}\s+", line):
            continue
        # 09:18 Oslo / 14:20 Myrdal via Train
        place = re.sub(r"^\d{1,2}:\d{2}\s+", "", line)
        place = re.split(r"\s+via\s+|\s+Via\s+", place, maxsplit=1)[0].strip(" -:|,")
        place = _polish_overview_item(place)
        if place and place not in places:
            places.append(place)
    return places


def _norway_nutshell_lines(row):
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
    if "norway in a nutshell" not in text:
        return []
    places = _extract_timed_route_places(row)
    lines = []
    base = get_travel_sequence_line(row)
    if places and len(places) >= 2:
        lines.append(f"Scenic Rail & Fjord Journey from {places[0]} to {places[-1]}")
        lines.append("Route: " + " → ".join(places))
    elif base:
        lines.append(base)
    includes = polish_inclusion_items([clean_include_item(item, row.get("title", "")) for item in normalize_list(row.get("includes", []))])
    if includes:
        lines.append("Included journey: " + ", ".join(includes))
    return lines


def _inline_arrival_time(row):
    text = f'{row.get("title", "")} {row.get("details", "")} {row.get("original_title", "")}'
    match = re.search(r"\barrival\s+to\s+[A-Za-zÀ-ÿøØåÅäÄöÖ\s]+\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm))", text, flags=re.IGNORECASE)
    if match:
        return display_time(match.group(1))
    if get_row_type(row) == "Cruise" and "overnight" in text.lower():
        times = re.findall(r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b", text, flags=re.IGNORECASE)
        if len(times) >= 2:
            return display_time(times[-1])
    return ""


def get_travel_arrangement_line(row):
    title = get_travel_sequence_line(row)
    time = display_time(row.get("time", "")) or _inline_arrival_time(row)
    duration = polish_client_text(row.get("duration", ""))
    details = []

    if time:
        details.append(time)
    arrival_time = _inline_arrival_time(row)
    if arrival_time and arrival_time != time:
        details.append(f"arrives {arrival_time}")
    if get_row_type(row) == "Cruise":
        cabin_match = re.search(r"\b(?:\d+\s*x\s*)?Cabin\s*\(([^)]+)\)", f'{row.get("details", "")} {row.get("original_title", "")}', flags=re.IGNORECASE)
        if cabin_match:
            details.append(f"{polish_title(cabin_match.group(1))} cabin")
    if duration and " - " not in time:
        clean_duration = format_duration_display(duration)
        if clean_duration:
            details.append(clean_duration)

    return f"{title} — {'; '.join(details)}" if details else title


def build_travel_arrangements_block(travel_rows):
    items = []
    for row in travel_rows:
        special_lines = _norway_nutshell_lines(row)
        if special_lines:
            for line in special_lines:
                if line and line not in items:
                    items.append(line)
            continue
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
    departure_day = any(get_row_type(row) == "Departure" for row in rows)

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
            if departure_day and row_type == "Transfer" and "to your accommodation" in str(row.get("title", "")).lower():
                row = dict(row)
                city = get_primary_city(rows) or row.get("city", "")
                row["title"] = f"Private transfer from your hotel to {polish_title(city)} Airport" if city else "Private transfer from your hotel to the airport"
            travel_group.append(row)
            continue

        flush_travel_group()

        if row_type == "Departure":
            blocks.append(build_departure_block(row))
        elif row_type == "Day Overview":
            block = build_day_overview_block(row)
            if block:
                blocks.append(block)
        elif row_type == "Hotel":
            blocks.append(build_accommodation_block(row))
        elif row_type == "Arrival":
            blocks.append(build_arrival_block(row))
        elif row_type == "Activity":
            blocks.append(build_activity_block(row))
        elif row_type == "Leisure":
            blocks.append(build_leisure_block(row))
        elif _is_cruise_leisure_row(row):
            blocks.append(build_cruise_leisure_block(row))
        elif title:
            included_block = build_included_today_block([polish_title(title)])
            if included_block:
                blocks.append(included_block)

    flush_travel_group()
    return blocks
