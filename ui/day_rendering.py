"""HTML/day rendering helpers for the Streamlit itinerary app.

This module is intentionally UI-rendering focused. It was split out of
app.py so the Streamlit entrypoint can remain a coordinator while the
client-facing itinerary blocks live in one place.
"""

import html
import re

from generator import (
    TRANSPORT_TYPES,
    clean_include_item,
    create_client_activity_title,
    create_day_intro,
    create_day_title,
    get_primary_city,
    get_row_type,
    get_transfer_travel_title,
    is_route_transfer,
    is_self_arranged,
)
from text_polish import (
    expand_time_with_duration,
    format_duration_display,
    polish_client_text,
    polish_hotel_name,
    polish_inclusion_item,
    polish_inclusion_items,
    polish_title,
)
from itinerary_parser import normalize_time_text
from layout_policy import (
    DEFAULT_DAY_PAGE_LAYOUT,
    is_day_packing_enabled,
    is_three_day_packing_enabled as policy_is_three_day_packing_enabled,
    normalize_day_page_layout,
)
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES
from ui.editor_sanitizer import clean_visual_editor_html
from images.app_image_selection import render_day_image_slot, select_day_images_with_overrides


def get_detail_level_name(output_edits=None):
    """Return the fixed rich descriptive level used by the current app output."""
    return "Rich descriptive"


def get_day_page_layout_name(output_edits=None):
    """Return a safe day page layout from editable output state.

    This mirrors the app-level helper but keeps packing/rendering helpers
    self-contained after the UI split.
    """
    name = (output_edits or {}).get("day_page_layout") or DEFAULT_DAY_PAGE_LAYOUT
    return normalize_day_page_layout(name)


def is_smart_day_packing_enabled(output_edits=None):
    return is_day_packing_enabled(get_day_page_layout_name(output_edits))


def is_three_day_packing_enabled(output_edits=None):
    return policy_is_three_day_packing_enabled(get_day_page_layout_name(output_edits))

def esc(value):
    return html.escape(str(value or ""), quote=True)


def clean_space(value):
    """Small local whitespace normalizer used by UI/helper functions.

    The parser has its own clean_space helper, but app.py should not depend on
    private parser helpers at runtime. Keeping this local prevents UI helper
    functions from raising NameError when they clean pickup/drop-off text.
    """
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def normalize_list(items):
    if not items:
        return []

    if isinstance(items, list):
        return [str(item).strip() for item in items if item and str(item).strip()]

    if isinstance(items, str):
        return [item.strip() for item in items.split(",") if item.strip()]

    return []


def list_to_text(items):
    return "\n".join(normalize_list(items))


def text_to_list(value):
    if not value:
        return []

    clean_items = []

    for line in str(value).splitlines():
        item = line.strip()
        item = item.lstrip("•").lstrip("-").strip()

        if item:
            clean_items.append(item)

    return clean_items


def display_time(value):
    return normalize_time_text(value)


def display_time_with_duration(time_value, duration_value):
    """Show a clear start-end time when a reliable start time and duration exist.

    This is the single day-by-day display rule the user requested:
    if an activity has one start time plus a duration, show the calculated
    end time in the Time line.
    """
    return expand_time_with_duration(display_time(time_value), duration_value)


def detect_hotel_pickup_dropoff_text(value):
    """Return a clean pickup/drop-off phrase when supplier text says hotel pickup is included."""

    text = clean_space(value)
    if not text:
        return ""

    lower = text.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lower)
    normalized = f" {clean_space(normalized)} "

    has_hotel_context = any(
        marker in normalized
        for marker in [
            " hotel ",
            " hotels ",
            " accommodation ",
            " accommodations ",
            " your hotel ",
            " selected hotel ",
            " centrally located hotel ",
            " central hotel ",
        ]
    )
    has_pickup = any(marker in normalized for marker in [" pick up ", " pickup ", " picked up ", " collection "])
    has_dropoff = any(marker in normalized for marker in [" drop off ", " dropoff ", " dropped off ", " return transfer "])

    if has_hotel_context and has_pickup and has_dropoff:
        return "Hotel pick-up and drop-off"

    if has_hotel_context and has_pickup:
        return "Hotel pick-up"

    # Compact supplier phrasing sometimes omits the word hotel in the exact
    # pickup phrase but still clearly says pickup/drop-off is included.
    if ("pick up drop off" in normalized or "pickup dropoff" in normalized or "pickup drop off" in normalized) and has_hotel_context:
        return "Hotel pick-up and drop-off"

    return ""


def clean_pickup_dropoff_value(value):
    """Normalize a pickup/drop-off detail for display."""

    text = clean_space(value).strip(" :.-")
    if not text:
        return ""

    hotel_phrase = detect_hotel_pickup_dropoff_text(text)
    if hotel_phrase:
        return hotel_phrase

    text = re.sub(r"^(pick[- ]?up\s*/\s*drop[- ]?off\s*)", "", text, flags=re.IGNORECASE).strip(" :.-")
    text = re.sub(r"^(pick[- ]?up\s+and\s+drop[- ]?off\s*)", "", text, flags=re.IGNORECASE).strip(" :.-")
    text = re.sub(r"^(pickup\s+and\s+dropoff\s*)", "", text, flags=re.IGNORECASE).strip(" :.-")

    # Sometimes supplier inclusions arrive as one comma-separated bullet such as
    # "Pick-up/drop-off in central Tromsø, English-speaking guide". Only the
    # actual logistics portion belongs in the day-by-day pickup line.
    text = re.split(
        r",\s*(?=(?:english[- ]speaking|knowledgeable|professional|comfortable|northern lights|warm |snacks|drinks|free photographs|2-course|tour transportation|guide)\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" :.-")

    return text or value


def get_activity_logistics(row):
    """Return a practical meeting/pick-up line for the day-by-day block."""

    meeting_point = str(row.get("meeting_point") or "").strip()
    if meeting_point:
        hotel_phrase = detect_hotel_pickup_dropoff_text(meeting_point)
        if hotel_phrase:
            return "Pick-up/drop-off", hotel_phrase
        return "Meeting point", meeting_point

    for item in normalize_list(row.get("includes", [])):
        item_text = str(item).strip()
        lower = item_text.lower()

        hotel_phrase = detect_hotel_pickup_dropoff_text(item_text)
        if hotel_phrase:
            return "Pick-up/drop-off", hotel_phrase

        if (
            "pick-up/drop-off" in lower
            or "pickup/drop-off" in lower
            or "pick up/drop-off" in lower
            or "pick-up and drop-off" in lower
            or "pick up and drop off" in lower
            or "pickup and dropoff" in lower
        ):
            value = clean_pickup_dropoff_value(item_text)
            return "Pick-up/drop-off", value or item_text

        if lower.startswith("departure from") or "drop-off" in lower or "drop off" in lower:
            return "Departure/drop-off", item_text

    detail_text = " ".join(
        str(row.get(key) or "")
        for key in ["title", "original_title", "details", "client_description"]
    )
    hotel_phrase = detect_hotel_pickup_dropoff_text(detail_text)
    if hotel_phrase:
        return "Pick-up/drop-off", hotel_phrase

    return "", ""


def render_list_items(items, class_name="detail-list"):
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    html_text = f'<ul class="{esc(class_name)}">'

    for item in clean_items:
        html_text += f"<li>{esc(item)}</li>"

    html_text += "</ul>"

    return html_text


def get_time_period(time_text):
    if not time_text:
        return "Featured experience"

    text = time_text.lower()
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)

    if not match:
        # 24-hour format support.
        match_24 = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
        if not match_24:
            return "Featured experience"

        hour = int(match_24.group(1))
    else:
        hour = int(match.group(1))
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12

        if period == "am" and hour == 12:
            hour = 0

    if hour < 12:
        return "Morning Experience"

    if 12 <= hour < 17:
        return "Afternoon Experience"

    return "Evening Experience"


def plural_nights(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if value == "1":
        return "1 night"

    return f"{value} nights"


def meal_phrase(value):
    value = str(value or "").strip()

    if not value:
        return ""

    lower = value.lower()

    if lower.startswith("with ") or lower.startswith("without "):
        return value

    if lower in ["breakfast", "dinner", "half board", "full board", "breakfast and dinner"]:
        return f"with {lower}"

    return f"with {value}"


def is_self_arranged_transport(row):
    return (get_row_type(row) in TRANSPORT_TYPES or is_route_transfer(row)) and is_self_arranged(row)


def get_activity_description(row, detail_level=None):
    detail_level = detail_level or get_detail_level_name()
    title = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    city = str(row.get("city", "")).strip().lower()

    if "fjellheisen" in title or "round trip ticket" in title:
        if detail_level == "Elegant concise":
            return "Ride Fjellheisen for panoramic views over Tromsø."
        if detail_level == "Rich descriptive":
            return "Ride the Fjellheisen cable car for sweeping views over Tromsø, the surrounding islands, fjords, and mountain scenery."
        return "Enjoy panoramic views over Tromsø, the surrounding islands, fjords, and mountains."

    if "lofoten" in title and "trollfjord" in title:
        if detail_level == "Elegant concise":
            return "Travel through Lofoten by land and sea, including Trollfjord scenery."
        if detail_level == "Rich descriptive":
            return "Experience Lofoten by land and sea, with time around Stokmarknes and a scenic cruise into the dramatic Trollfjord landscape."
        return "Travel through Lofoten by land and sea, with time around Stokmarknes and a cruise into the dramatic Trollfjord."

    if "city walking" in title and "canal" in title and "copenhagen" in title:
        if detail_level == "Elegant concise":
            return "Explore Copenhagen on foot and by canal with a local host."
        if detail_level == "Rich descriptive":
            return "Explore central Copenhagen with a local host, combining city landmarks, local stories, and a scenic canal experience."
        return "Explore central Copenhagen on foot with a local host, including key landmarks and a scenic canal experience."

    if "essential oslo" in title:
        if detail_level == "Elegant concise":
            return "Explore central Oslo on foot with a local guide."
        if detail_level == "Rich descriptive":
            return "Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital."
        return "Explore central Oslo on foot with a local guide, including key landmarks around the city center."

    if "guided walking tour" in title:
        if "copenhagen" in city or "copenhagen" in title:
            if detail_level == "Elegant concise":
                return "Explore central Copenhagen on foot with a local guide."
            if detail_level == "Rich descriptive":
                return "Explore central Copenhagen on foot with a local guide, with time for local stories, major landmarks, and the atmosphere of the city."
            return "Explore central Copenhagen on foot with a local guide, with time for local stories and key city landmarks."
        if "oslo" in city or "oslo" in title:
            if detail_level == "Elegant concise":
                return "Explore central Oslo on foot with a local guide."
            if detail_level == "Rich descriptive":
                return "Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital."
            return "Explore central Oslo on foot with a local guide, including key landmarks around the city center."

    if "must-see bergen" in title or ("foot and boat" in title and "bergen" in title):
        if detail_level == "Elegant concise":
            return "Explore Bergen on foot and by boat."
        if detail_level == "Rich descriptive":
            return "Explore Bergen from two perspectives: on foot through the historic city streets and by boat from the surrounding waters."
        return "Explore Bergen on foot and by boat, combining historic city streets with a scenic perspective from the water."

    if "hop on" in title or "hop-on" in title or "hop off" in title or "hop-off" in title:
        if detail_level == "Rich descriptive":
            return "Use your flexible ticket to explore the city at your own pace, choosing the stops and sights that suit your day best."
        return "Use your flexible ticket to explore the city at your own pace."

    if "tallinn" in title:
        if detail_level == "Elegant concise":
            return "Travel from Helsinki to Tallinn and explore the Old Town."
        if detail_level == "Rich descriptive":
            return "Travel from Helsinki to Tallinn and enjoy time in the atmospheric Old Town before returning to Helsinki."
        return "Travel from Helsinki to Tallinn and enjoy time to explore the historic Old Town before returning to Helsinki."

    clean_title = polish_title(create_client_activity_title(row) or row.get("title", "") or "Included experience")
    city_name = polish_title(row.get("city", ""))
    combined = f"{clean_title} {title}".lower()

    # Fallback descriptions should add atmosphere, not repeat logistics already
    # shown in the Time / Duration / Pick-up lines.
    if "suomenlinna" in combined:
        return "A guided introduction to Helsinki’s city highlights combined with a visit to the historic sea fortress island of Suomenlinna."
    if "northern lights basecamp" in combined:
        return "Spend the evening at a dedicated Northern Lights basecamp, with time to wait for the aurora in a comfortable Arctic setting."
    if "northern lights" in combined or "aurora" in combined:
        if "hunt" in combined or "chase" in combined:
            return "Head out in search of the Northern Lights with local guidance, using the evening conditions to find the best available viewing areas."
        if "floating" in combined or "float" in combined:
            return "Experience the Arctic night from a peaceful frozen-lake setting, with specialist equipment provided for the ice-floating experience."
        return "Enjoy an evening Northern Lights experience designed around the Arctic sky, local conditions, and the chance to see the aurora."
    if "santa claus village" in combined and "reindeer" in combined:
        return "Visit Santa Claus Village and enjoy a classic Arctic reindeer experience, combining festive atmosphere with a memorable Lapland tradition."
    if "ranua" in combined or "wildlife" in combined:
        return "Travel to Ranua Wildlife Park for a look at Arctic wildlife in a forested Lapland setting, with time to enjoy the experience at an easy pace."
    if "fjord tour" in combined or "kvaløya" in combined or "sommarøy" in combined:
        return "Explore the coastal scenery around Tromsø, with fjords, islands and Arctic landscapes forming the focus of the day."
    if "fjellheisen" in combined or "cable car" in combined:
        return "Ride the Fjellheisen cable car for sweeping views over Tromsø, the surrounding islands, fjords, and mountain scenery."
    if "funicular" in combined or "fløibanen" in combined:
        return "Ride the Fløibanen funicular for an easy ascent above Bergen and views over the city, harbour and surrounding mountains."

    destination_phrase = f" in {city_name}" if city_name else ""
    if "walking" in combined or "guided" in combined:
        return f"Enjoy a guided experience{destination_phrase}, with local context and a clear route through the day’s main highlights."
    if "boat" in combined or "cruise" in combined or "canal" in combined:
        return f"See the destination from the water, adding a scenic perspective to the day’s planned experience{destination_phrase}."
    return f"Enjoy a planned experience{destination_phrase}, adding a clear highlight to the day while keeping the wider itinerary easy to follow."


def is_self_transfer(row):
    row_type = get_row_type(row)
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()

    return row_type == "Transfer" and "self transfer" in text


def is_tallinn_ferry_day_trip(row):
    """Return True for Helsinki-Tallinn ferry-style day trip activities.

    Supplier rows often call the crossing a cruise ticket even though the
    client-facing product is a ferry-style Tallinn day trip. Keep this broad
    enough for self-guided and guided formats, but still tied to Tallinn.
    """

    context_text = " ".join(
        str(row.get(key) or "")
        for key in ["city", "title", "original_title", "details", "client_description"]
    ).lower()
    context_text += " " + " ".join(normalize_list(row.get("includes", []))).lower()

    mentions_tallinn = "tallinn" in context_text or "tallin" in context_text
    if not mentions_tallinn:
        return False

    # A day-trip title from Helsinki to Tallinn is enough context for the
    # duration label to be "Ferry duration" even when the raw row says cruise.
    if "day trip to tallinn" in context_text or "excursion to tallinn" in context_text or "excursion to tallin" in context_text:
        return True

    mentions_helsinki = "helsinki" in context_text
    crossing_marker = any(
        marker in context_text
        for marker in [
            "star class",
            "cruise ticket",
            "ferry ticket",
            "port transfer",
            "port transfers",
            "departure from helsinki",
            "departure from tallinn",
            "helsinki port",
            "ferry crossing",
        ]
    )

    return mentions_tallinn and (mentions_helsinki or crossing_marker) and crossing_marker


def get_activity_duration_label(row, duration):
    """Return a conservative client-facing duration label for an activity.

    Most experiences should simply say "Duration". A tour can include a ferry,
    canal boat, or cruise element without the full activity length being a
    ferry/cruise duration. Use ferry/cruise labels only when the row or duration
    text clearly supports that wording.
    """

    row_type = get_row_type(row)
    duration_text = str(duration or "").lower().strip()

    if is_tallinn_ferry_day_trip(row):
        return "Ferry duration"

    if re.match(r"^ferry\s+duration\b", duration_text, flags=re.IGNORECASE):
        return "Ferry duration"

    if re.match(r"^cruise\s+duration\b", duration_text, flags=re.IGNORECASE):
        return "Cruise duration"

    if row_type == "Ferry":
        return "Ferry duration"

    if row_type == "Cruise":
        return "Cruise duration"

    return "Duration"


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
    title = polish_title(row.get("title", "") or "Departure home")

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


def get_important_travel_notes(output_edits=None):
    if output_edits and output_edits.get("important_travel_notes_text"):
        return text_to_list(output_edits.get("important_travel_notes_text"))
    return DEFAULT_IMPORTANT_TRAVEL_NOTES


def get_fallback_activity_inclusions(row):
    """Create sensible client-facing inclusions when supplier text has no formal inclusion list."""

    title = create_client_activity_title(row) or row.get("title", "")
    source_items = normalize_list(row.get("includes", []))
    full_text = " ".join(
        [str(title), str(row.get("original_title", "")), str(row.get("details", ""))]
        + [str(item) for item in source_items]
    ).lower()

    if "tallin" in full_text or "tallinn" in full_text or title == "Day Trip to Tallinn":
        inclusions = []
        if "port transfer" in full_text or "helsinki port" in full_text or "hotel pick" in full_text:
            inclusions.append("Helsinki port transfers")
        if "star class" in full_text:
            inclusions.append("Star Class ferry ticket")
        elif "ferry ticket" in full_text or "cruise ticket" in full_text or "day trip to tallinn" in str(title).lower():
            inclusions.append("Helsinki–Tallinn ferry crossing")
        if "guided" in full_text and ("old town" in full_text or "tallinn" in full_text or "tallin" in full_text):
            inclusions.append("Guided Old Town tour")
        if not inclusions:
            inclusions = ["Helsinki–Tallinn ferry crossing", "Time to explore Tallinn Old Town"]
        return inclusions

    if "essential oslo" in full_text or ("oslo" in full_text and "walking tour" in full_text):
        return ["Guided walking tour"]

    if "must-see bergen" in full_text or ("bergen" in full_text and "foot and boat" in full_text):
        return ["Guided walking tour", "Boat tour"]

    if "hop-on hop-off" in title.lower() or "hop on" in full_text or "hop-off" in full_text or "hop off" in full_text:
        return ["24-hour Hop-On Hop-Off bus ticket"]

    if "fløibanen" in full_text or "floibanen" in full_text:
        if "round" in full_text or "roundtrip" in full_text or "round trip" in full_text:
            return ["Round-trip Fløibanen ticket"]
        return ["Fløibanen ticket"]

    if "walking" in full_text and "canal" in full_text:
        return ["Guided walking tour", "Canal experience"]

    if "walking tour" in full_text or "guided" in full_text:
        return ["Guided experience"]

    if "ticket" in full_text:
        return ["Ticket"]

    return []


def prioritize_inline_inclusions(items, max_items=5):
    """Keep inline inclusions premium and compact.

    Day pages should show the most useful inclusions without turning into an
    appendix. Prefer logistics, guide, transport, tickets/entrance, meals and
    special equipment; drop low-value accounting items when space is limited.
    """

    clean_items = []
    for item in polish_inclusion_items(normalize_list(items)):
        if not item or item in clean_items:
            continue
        lower = item.lower()
        if lower in {"guided experience", "experience as described in the day-by-day itinerary"} and len(items) > 1:
            continue
        if any(marker in lower for marker in ["tax", "service fee", "goods and services"]):
            continue
        clean_items.append(item)

    def score(item):
        lower = item.lower()
        if "pick" in lower or "drop" in lower or "transfer" in lower:
            return 0
        if "guide" in lower or "guided" in lower:
            return 1
        if "transport" in lower or "coach" in lower or "minivan" in lower or "bus" in lower:
            return 2
        if "ticket" in lower or "entrance" in lower or "ferry" in lower or "certificate" in lower:
            return 3
        if "meal" in lower or "lunch" in lower or "dinner" in lower or "drink" in lower or "snack" in lower or "cookies" in lower:
            return 4
        if "photo" in lower or "camera" in lower or "thermal" in lower or "overall" in lower or "tripod" in lower:
            return 5
        return 6

    ordered = sorted(enumerate(clean_items), key=lambda pair: (score(pair[1]), pair[0]))
    selected = [item for _, item in ordered[:max_items]]
    # Restore original order among selected items so the client-facing flow feels natural.
    return [item for item in clean_items if item in selected]


def looks_like_descriptive_prose(text):
    lower = str(text or "").lower()
    prose_markers = [
        "tour gives",
        "take a stroll",
        "listen to",
        "make sense",
        "to top it all",
        "waterworld",
        "best way to understand",
        "explore bergen from",
        "historic city streets",
    ]
    return len(str(text or "")) > 95 and any(marker in lower for marker in prose_markers)


def clean_activity_inclusion_items(items, title=""):
    clean_items = []
    for item in normalize_list(items):
        text = polish_inclusion_item(str(item).strip(), title)
        lower = text.lower().strip(":? ")

        text = re.split(r"\s+-\s+(?:Description|Overview)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
        lower = text.lower().strip(":? ")

        if lower in {"what's included", "what’s included", "includes", "included", "description", "overview"}:
            continue

        # Avoid long overview prose on the inclusion page.
        if looks_like_descriptive_prose(text):
            continue
        if len(text) > 150 and "included" not in lower:
            continue

        text = polish_inclusion_item(clean_include_item(text, title), title)
        if text and text not in clean_items:
            clean_items.append(text)

    clean_items = polish_inclusion_items(clean_items, title)
    if not clean_items or all(looks_like_descriptive_prose(item) for item in clean_items):
        return []
    return clean_items


def create_activity_inclusions(parsed_rows):
    activity_sections = []

    for row in parsed_rows:
        if get_row_type(row) != "Activity":
            continue

        title = create_client_activity_title(row) or row.get("title", "")
        title = str(title).strip()
        includes = clean_activity_inclusion_items(row.get("includes", []), title)

        # Every activity should be represented on this page. If the supplier
        # text does not contain a formal inclusion list, use a conservative
        # fallback based on the activity type.
        if not includes:
            includes = get_fallback_activity_inclusions(row)

        if not title or not includes:
            continue

        activity_sections.append({
            "title": title,
            "includes": includes,
            "is_optional": bool(row.get("is_optional")),
        })

    return activity_sections


def create_optional_addons(parsed_rows):
    optional_rows = [row for row in parsed_rows if row.get("is_optional")]
    addons = []

    for row in optional_rows:
        row_type = get_row_type(row)
        title = create_client_activity_title(row) if row_type == "Activity" else row.get("title", "")
        title = str(title or row.get("title", "Optional add-on")).strip()
        city = str(row.get("city", "")).strip()
        if row_type == "Activity" and title.lower() in {"svolvær", "svolvaer", "svolaver", "svoalvaer"}:
            title = "Optional experience in Svolvær"
        time = display_time(row.get("time", ""))
        duration = str(row.get("duration", "")).strip()
        includes = polish_inclusion_items([clean_include_item(item, title) for item in normalize_list(row.get("includes", []))], title)
        if row_type == "Activity" and not includes:
            includes = get_fallback_activity_inclusions(row)
        meeting_label, meeting_point = get_activity_logistics(row) if row_type == "Activity" else ("", "")

        if not title:
            continue

        if row_type in TRANSPORT_TYPES or is_self_arranged_transport(row):
            label = "Optional self-arranged travel" if is_self_arranged(row) else "Optional travel"
        elif row_type == "Transfer":
            label = "Optional transfer"
        elif row_type == "Activity":
            label = "Optional experience"
        else:
            label = "Optional add-on"

        addons.append({
            "day": row.get("day", ""),
            "label": label,
            "title": title,
            "city": city,
            "time": time,
            "duration": duration,
            "meeting_label": meeting_label,
            "meeting_point": meeting_point,
            "includes": includes,
        })

    return addons


def estimate_activity_inclusion_units(section):
    """Estimate how much vertical space an inclusion section needs on an A4 page.

    The goal is to avoid the old fixed-count split where six compact sections
    became five sections on one page and a nearly empty continued page. The
    estimate intentionally stays conservative for long bullet text, while still
    allowing compact ticket-style sections to share a page.
    """

    includes = normalize_list(section.get("includes", []))
    title_units = 2.1
    bullet_units = 0

    for item in includes:
        # One normal bullet line plus extra allowance for wrapped text.
        bullet_units += 0.9 + max(0, (len(str(item)) - 86) / 86)

    # Small spacing between activity sections.
    return title_units + bullet_units + 0.55


def chunk_activity_inclusions(activity_sections, max_units=43):
    chunks = []
    current_chunk = []
    current_units = 0

    for section in activity_sections:
        section_units = estimate_activity_inclusion_units(section)

        if current_chunk and current_units + section_units > max_units:
            chunks.append(current_chunk)
            current_chunk = [section]
            current_units = section_units
        else:
            current_chunk.append(section)
            current_units += section_units

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def render_activity_inclusions_pages(activity_sections):
    if not activity_sections:
        return ""

    html_text = ""
    chunks = chunk_activity_inclusions(activity_sections)

    for index, chunk in enumerate(chunks):
        continued = "" if index == 0 else " continued"

        html_text += f"""
        <div class="a4-page final-list-page activity-inclusions-page">
            <div class="final-page-title">Activity inclusions{continued}</div>
        """

        for section in chunk:
            html_text += '<div class="activity-inclusion-block">'
            optional_label = "Optional: " if section.get("is_optional") else ""
            html_text += f'<div class="activity-inclusion-title">{esc(optional_label + section["title"])}</div>'
            html_text += render_list_items(section["includes"], class_name="final-list")
            html_text += "</div>"

        html_text += "</div>"

    return html_text


def render_optional_addons_pages(optional_addons, items_per_page=8):
    if not optional_addons:
        return ""

    html_text = ""

    for start in range(0, len(optional_addons), items_per_page):
        chunk = optional_addons[start:start + items_per_page]
        continued = "" if start == 0 else " continued"
        html_text += f'''
        <div class="a4-page final-list-page optional-addons-page">
            <div class="final-page-title">Optional add-ons{continued}</div>
        '''

        for addon in chunk:
            html_text += '<div class="activity-inclusion-block optional-addon-block">'
            heading_bits = [addon.get("day", ""), addon.get("title", "")]
            heading = " — ".join([bit for bit in heading_bits if bit])
            html_text += f'<div class="activity-inclusion-title">{esc(heading)}</div>'
            html_text += f'<div class="body-text"><span class="meta-label">Type:</span> {esc(addon.get("label", "Optional add-on"))}</div>'

            if addon.get("city"):
                html_text += f'<div class="body-text"><span class="meta-label">Location:</span> {esc(addon["city"])}</div>'
            if addon.get("time"):
                html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(addon["time"])}</div>'
            if addon.get("duration"):
                html_text += f'<div class="body-text"><span class="meta-label">Duration:</span> {esc(format_duration_display(addon["duration"]))}</div>'
            if addon.get("meeting_point"):
                html_text += f'<div class="body-text"><span class="meta-label">{esc(addon.get("meeting_label") or "Meeting point")}:</span> {esc(addon["meeting_point"])}</div>'
            if addon.get("includes"):
                html_text += '<div class="section-title small-section">Includes</div>'
                html_text += render_list_items(addon["includes"], class_name="final-list")

            html_text += "</div>"

        html_text += "</div>"

    return html_text
