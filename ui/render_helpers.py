"""Shared rendering helper functions for itinerary HTML/UI output."""

import html
import re

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    get_primary_city,
    get_row_type,
    is_self_arranged,
)
from itinerary_generation.day_text import create_day_intro
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.titles import create_client_activity_title, create_day_title
from itinerary_generation.transport import get_transfer_travel_title, is_route_transfer
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


def get_detail_level_name(output_edits=None):
    """Return the fixed rich descriptive level used by the current app output."""
    return "Rich descriptive"


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

    if lower == "breakfast":
        return "breakfast included"
    if lower == "breakfast and dinner":
        return "breakfast and dinner included"
    if lower in ["dinner", "half board", "full board"]:
        return f"{lower} included"

    return f"with {value}"


def is_self_arranged_transport(row):
    return (get_row_type(row) in TRANSPORT_TYPES or is_route_transfer(row)) and is_self_arranged(row)


def get_activity_description(row, detail_level=None):
    detail_level = detail_level or get_detail_level_name()
    title = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    city = str(row.get("city", "")).strip().lower()

    if "wildlife photography" in title and "longyearbyen" in title:
        return "Spend time looking for Arctic wildlife and landscape photo opportunities around Longyearbyen with the guidance arranged for the experience."

    if "mountain hike" in title and "abisko" in title:
        return "Hike in the Abisko mountain landscape, with time for views, local nature stories and the included food stop during the excursion."

    if "fjord" in title and ("minivan" in title or "vip" in title or "kvaløya" in title or "sommarøy" in title):
        return "Explore the coastal scenery around Tromsø by road, with fjords, mountains, beaches and Arctic landscapes forming the focus of the day."

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
            return "Experience Lofoten by land and sea, with a scenic cruise into the dramatic Trollfjord landscape."
        return "Travel through Lofoten by land and sea, with a scenic cruise into the dramatic Trollfjord."

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
    destination_phrase = f" in {city_name}" if city_name else ""
    combined = f"{clean_title} {title}".lower()

    # Fallback descriptions should add atmosphere, not repeat logistics already
    # shown in the Time / Duration / Pick-up lines. They must never inject
    # destination-specific content that is not supported by the current row.
    if "blue lagoon" in combined or "sky lagoon" in combined or "lagoon" in combined and ("admission" in combined or "spa" in combined or "ritual" in combined):
        return "Enjoy this lagoon and wellness experience, with admission details arranged as part of the day."
    if "whale watching" in combined or "whale" in combined:
        return f"Join a whale watching experience{destination_phrase}, with time on the water and guidance from the local crew."
    if "snork" in combined or "silfra" in combined:
        return f"Experience Silfra with the arranged equipment and local guidance, following the meeting details provided for the activity."
    if "atv" in combined or "quad" in combined:
        return f"Head out on an ATV experience, with safety equipment and guidance provided for the route."
    if "glacier" in combined or "crampon" in combined:
        return f"Join a guided glacier experience, with the required safety equipment provided before heading onto the ice."
    if "suomenlinna" in combined:
        return "A guided introduction to Helsinki’s city highlights combined with a visit to the historic sea fortress island of Suomenlinna."
    if "korouoma" in combined or "frozen waterfall" in combined:
        return "Explore Korouoma Canyon on a guided winter hike, with frozen waterfalls, snowy forest scenery and a warm barbecue break included along the way."
    if "santa claus village" in combined and "snowmobile" in combined and "reindeer" in combined:
        return "Travel by snowmobile towards Santa Claus Village, with time for the festive village atmosphere and a short reindeer sleigh experience in the Arctic setting."
    if "santa claus village" in combined and "reindeer" in combined:
        return "Visit Santa Claus Village and enjoy a classic Arctic reindeer experience, combining festive atmosphere with a memorable Lapland tradition."
    if ("reindeer feeding" in combined or "sámi" in combined or "sami" in combined) and not ("northern lights chase" in combined or "northern lights hunt" in combined or "aurora hunt" in combined):
        return "Meet the reindeer herd, learn about Sámi culture and enjoy a warm meal as part of the Arctic experience."
    if "northern lights basecamp" in combined:
        return "Spend the evening at a dedicated Northern Lights basecamp, with time to wait for the aurora in a comfortable Arctic setting."
    if "northern lights" in combined or "aurora" in combined:
        if "reindeer" in combined and ("hunt" in combined or "chase" in combined):
            return "Head into the winter landscape for a Northern Lights hunt by reindeer, with warm drinks and Arctic atmosphere included in the experience."
        if "bbq" in combined or "barbecue" in combined or "lappish" in combined:
            return "Head away from the city lights in search of the Northern Lights, with a Lappish barbecue and time by the fire in the winter landscape."
        if "hunt" in combined or "chase" in combined:
            return "Head out in search of the Northern Lights with local guidance, using the evening conditions to find the best available viewing areas."
        if "floating" in combined or "float" in combined:
            return "Experience the Arctic night from a peaceful frozen-lake setting, with specialist equipment provided for the ice-floating experience."
        return "Enjoy an evening Northern Lights experience designed around the Arctic sky, local conditions, and the chance to see the aurora."
    if "ranua" in combined:
        return "Travel to Ranua Wildlife Park for a look at Arctic wildlife in a forested Lapland setting, with time to enjoy the experience at an easy pace."
    if "wildlife" in combined:
        return f"Enjoy a wildlife-focused experience{destination_phrase}, with the details arranged as part of the day."
    if "fjord tour" in combined or "kvaløya" in combined or "sommarøy" in combined:
        return "Explore the coastal scenery around Tromsø, with fjords, islands and Arctic landscapes forming the focus of the day."
    if "fjellheisen" in combined or "cable car" in combined:
        return "Ride the Fjellheisen cable car for sweeping views over Tromsø, the surrounding islands, fjords, and mountain scenery."
    if "funicular" in combined or "fløibanen" in combined:
        return "Ride the Fløibanen funicular for an easy ascent above Bergen and views over the city, harbour and surrounding mountains."

    if "photo tour" in combined and ("fjord" in combined or "landscape" in combined):
        return f"Explore scenic fjords and Arctic landscapes{destination_phrase}, with guidance on viewpoints and photography along the way."
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
