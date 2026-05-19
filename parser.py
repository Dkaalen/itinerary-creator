import hashlib
import re


DETAIL_LABELS = [
    "Time",
    "Meeting point",
    "End point",
    "Includes",
    "Notable Sights",
    "Schedule",
    "Luggage included",
]

DETAIL_MARKERS = [f" - {label}:" for label in DETAIL_LABELS]
DAY_PATTERN = re.compile(r"^day\s+\d+", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")
KNOWN_TYPES = {
    "arrival",
    "transfer",
    "transport",
    "hotel",
    "activity",
    "leisure",
    "departure",
    "train",
    "flight",
    "cruise",
    "ferry",
}


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def normalize_type(value):
    return clean_space(value).title()


def looks_like_day(value):
    return bool(DAY_PATTERN.match(clean_space(value)))


def looks_like_date(value):
    return bool(DATE_PATTERN.match(clean_space(value)))


def looks_like_known_type(value):
    return clean_space(value).lower() in KNOWN_TYPES




COMMON_TEXT_REPLACEMENTS = [
    (r"\bNUtshell\b", "Nutshell"),
    (r"\bNutshell\b", "Nutshell"),
    (r"\bBrekafast\b", "Breakfast"),
    (r"\bBrekfast\b", "Breakfast"),
    (r"\bDoubel\b", "Double"),
    (r"\bArrnaged\b", "arranged"),
    (r"\bArranged\b", "arranged"),
    (r"\bTromso\b", "Tromsø"),
    (r"\bKakslauttenen\b", "Kakslauttanen"),
]


def fix_common_text(value):
    """Silently fixes small recurring spelling/capitalization issues in pasted itineraries."""

    text = str(value or "")

    for pattern, replacement in COMMON_TEXT_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"\bNorway\s+in\s+a\s+Nutshell\b", "Norway in a Nutshell", text, flags=re.IGNORECASE)
    text = re.sub(r"\bWi-FI\b", "Wi-Fi", text, flags=re.IGNORECASE)
    text = re.sub(r"\b4Star\b", "4 Star", text, flags=re.IGNORECASE)
    text = re.sub(r"\b3Star\b", "3 Star", text, flags=re.IGNORECASE)

    return clean_space(text) if "\n" not in text else text


def normalize_place_name(value):
    place = fix_common_text(clean_space(value))
    place = place.strip(" .,-|:")

    # Remove service/product wording that should not appear in clean day titles.
    place = re.sub(r"^(Flight|Bus|Coach|Train|Transfer|Shuttle Transfer)\s+", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bArctic Resort\b", "", place, flags=re.IGNORECASE)
    place = re.sub(r"\bAirport\s+Airport\b", "Airport", place, flags=re.IGNORECASE)
    place = re.sub(r"\s+", " ", place).strip(" .,-|:")

    return place


def extract_route_points(text):
    """Returns (origin, destination) from common route phrasings."""

    source = fix_common_text(text)
    source = source.replace("–", "-")

    patterns = [
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+-\s+|\s+\|\s+|,|$)",
        r"\|\s*([^|\n]+?)\s+to\s+([^|\n]+?)\s*(?:\||$)",
        r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+-\s+|\s+\|\s+|,|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            continue

        origin = normalize_place_name(match.group(1))
        destination = normalize_place_name(match.group(2))

        # Avoid private shorthand being treated as cities in route titles.
        if destination.lower() in {"hotel", "station", "airport", "accommodation"}:
            continue

        return origin, destination

    return "", ""


def city_airport(city):
    city = normalize_place_name(city)
    return f"{city} Airport" if city else "the destination airport"


def standardize_private_transfer_title(title, details, city):
    text = fix_common_text(f"{title} {details}")
    lower = text.lower()
    airport = city_airport(city)

    if "hotel to airport" in lower or "accommodation to airport" in lower:
        return f"Private transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Private transfer from {airport} to your accommodation"

    if "hotel to station" in lower or "accommodation to station" in lower:
        return "Private transfer from your hotel to the station"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return "Private transfer from the station to your accommodation"

    if "airport" in lower and "hotel" not in lower and "accommodation" not in lower:
        if " to airport" in lower:
            return f"Private transfer to {airport}"
        if "airport to" in lower:
            return f"Private transfer from {airport}"

    if "to hotel" in lower or "to accommodation" in lower or "to your accommodation" in lower:
        return "Private transfer to your accommodation"

    return fix_common_text(title)


def standardize_self_transfer_title(title, details, city):
    text = fix_common_text(f"{title} {details}")
    lower = text.lower()
    airport = city_airport(city)

    if "hotel to airport" in lower or "accommodation to airport" in lower or "to airport" in lower:
        return f"Self-guided transfer from your hotel to {airport}"

    if "airport to hotel" in lower or "airport to accommodation" in lower:
        return f"Self-guided transfer from {airport} to your accommodation"

    if "hotel to station" in lower or "to station" in lower:
        return "Self-guided transfer from your hotel to the station"

    if "station to hotel" in lower or "station to accommodation" in lower:
        return "Self-guided transfer from the station to your accommodation"

    return fix_common_text(title).replace("Self transfer", "Self-guided transfer")


def create_clean_transport_title(row):
    row_type = row.get("effective_type") or row.get("type", "")
    title = fix_common_text(row.get("title", ""))
    details = fix_common_text(row.get("details", ""))
    text = f"{title} {details}"
    lower = text.lower()
    origin, destination = extract_route_points(details)
    if not destination:
        origin, destination = extract_route_points(title)
    if not destination:
        origin, destination = extract_route_points(text)
    city = normalize_place_name(row.get("city", ""))

    if "norway in a nutshell" in lower:
        if destination:
            return f"Norway in a Nutshell to {destination}"
        return "Norway in a Nutshell"

    if row_type == "Flight" or "flight" in lower:
        if destination:
            return f"Flight to {destination}"
        if city:
            return f"Flight to {city}"
        return "Flight"

    if row_type == "Train" or "train" in lower:
        prefix = "Overnight Train" if "overnight" in lower else "Train"
        if destination:
            return f"{prefix} to {destination}"
        if city:
            return f"{prefix} to {city}"
        return prefix

    if "coach" in lower or "bus" in lower:
        if destination:
            return f"Coach Transfer to {destination}"
        if city:
            return f"Coach Transfer to {city}"
        return "Coach Transfer"

    if row_type in {"Cruise", "Ferry"}:
        label = "Ferry" if row_type == "Ferry" else "Cruise"
        if destination:
            return f"{label} to {destination}"
        if city:
            return f"{label} to {city}"
        return label

    return title


def standardize_row_text(row):
    """Applies client-facing cleanup after row parsing and effective type detection."""

    for key in ["city", "title", "details", "time", "meeting_point", "end_point", "luggage_included", "hotel_name", "room_category", "meal_plan"]:
        if key in row and row.get(key):
            row[key] = fix_common_text(row[key])

    for key in ["notable_sights", "includes"]:
        if key in row and isinstance(row.get(key), list):
            row[key] = [fix_common_text(item) for item in row[key] if fix_common_text(item)]

    row_type = row.get("effective_type") or row.get("type", "")
    title = row.get("title", "")
    details = row.get("details", "")
    city = row.get("city", "")
    combined_lower = f"{title} {details}".lower()

    if row_type == "Transfer":
        if "self transfer" in combined_lower:
            row["title"] = standardize_self_transfer_title(title, details, city)
        elif "private" in combined_lower:
            row["title"] = standardize_private_transfer_title(title, details, city)

    if row_type in {"Transport", "Train", "Flight", "Cruise", "Ferry"}:
        row["title"] = create_clean_transport_title(row)

    return row


def extract_detail(text, label):
    marker = f"{label}:"

    if marker not in text:
        return ""

    after_marker = text.split(marker, 1)[1]

    for next_marker in DETAIL_MARKERS:
        if next_marker in after_marker:
            after_marker = after_marker.split(next_marker, 1)[0]

    return after_marker.strip(" -")


def extract_between_markers(text, start_patterns, stop_patterns):
    """
    Extract a section from long supplier-style descriptions.

    Used for colleague paste formats where cells contain blocks like:
    What's included?
    item
    item
    Pick up / meeting point
    address
    """

    if not text:
        return ""

    lowered = text.lower()
    starts = []

    for pattern in start_patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            starts.append(match.end())

    if not starts:
        return ""

    start = min(starts)
    section = text[start:]

    stop_positions = []
    section_lower = section.lower()

    for pattern in stop_patterns:
        match = re.search(pattern, section_lower, flags=re.IGNORECASE)
        if match:
            stop_positions.append(match.start())

    if stop_positions:
        section = section[:min(stop_positions)]

    return section.strip(" :|-\n\r\t")


def clean_title(text):
    """
    Removes labelled detail sections and long supplier text from a title.
    """

    title = clean_space(text)

    # Standard format: "Title - Time: ... - Includes: ..."
    for marker in DETAIL_MARKERS:
        if marker in title:
            title = title.split(marker, 1)[0]

    # Colleague format: "Title | 20:00 | 5 Hrs | Overview..."
    if "|" in title:
        title = title.split("|", 1)[0]

    # Prevent very long paragraphs from becoming titles.
    for marker in [
        "What's included",
        "What’s included",
        "Overview",
        "What to expect",
        "Pick up / meeting point",
        "Meeting point",
    ]:
        index = title.lower().find(marker.lower())
        if index > 0:
            title = title[:index]

    title = title.strip(" -:|")

    # Remove duplicated city prefix if the product title starts with "City: Title".
    if ":" in title:
        possible_city, rest = title.split(":", 1)
        if len(possible_city.strip()) <= 25 and rest.strip():
            title = rest.strip()

    return clean_space(title)


def split_comma_list(text, *, protect_compound_phrases=False):
    if not text:
        return []

    if isinstance(text, list):
        return [clean_space(item) for item in text if clean_space(item)]

    text = str(text).replace("\r", "\n")

    # Multiline supplier blocks should stay as one item per line.
    if "\n" in text:
        parts = []
        for line in text.splitlines():
            clean_line = clean_space(line.strip("•-* \t"))
            if clean_line:
                parts.append(clean_line)
    else:
        parts = [clean_space(item) for item in str(text).split(",") if clean_space(item)]

    if not protect_compound_phrases:
        return parts

    merged = []
    attach_to_previous_prefixes = (
        "english-speaking",
        "english speaker",
        "english - speaker",
        "norwegian-speaking",
        "norwegian speaker",
        "sami-speaking",
        "van or coach",
        "coach or van",
        "bus or coach",
    )

    for part in parts:
        lower = part.lower()

        if merged and lower.startswith(attach_to_previous_prefixes):
            merged[-1] = f"{merged[-1]}, {part}"
        else:
            merged.append(part)

    return merged


def detect_effective_type(item_type, title, details):
    combined = f"{title} {details}".lower().strip()

    if "flight to" in combined or combined.startswith("flight ") or re.search(r"\bflight\s*\|", combined):
        return "Flight"

    if "train to" in combined or "train transfer" in combined or "express train" in combined or "overnight train" in combined:
        return "Train"

    if "cruise to" in combined or "overnight cruise" in combined:
        return "Cruise"

    if "ferry to" in combined:
        return "Ferry"

    if (
        "coach transfer" in combined
        or combined.startswith("bus")
        or " bus " in f" {combined} "
        or "norway in a nutshell" in combined
    ) and "private" not in combined:
        return "Transport"

    return normalize_type(item_type)


def preprocess_raw_rows(raw_text):
    """
    Rebuild rows when Excel cells contain line breaks.

    A new row starts when one of the first few tab-separated cells contains
    "Day X". Lines that do not start a row are appended to the previous row.
    """

    rows = []
    current = ""

    for raw_line in raw_text.splitlines():
        if not raw_line.strip():
            continue

        parts = raw_line.split("\t")
        starts_new_row = any(looks_like_day(part) for part in parts[:4])

        if starts_new_row:
            if current.strip():
                rows.append(current)
            current = raw_line
        else:
            if current:
                current += "\n" + raw_line
            else:
                current = raw_line

    if current.strip():
        rows.append(current)

    return rows


def find_day_index(parts):
    for index, part in enumerate(parts[:5]):
        if looks_like_day(part):
            return index

    return None


def find_description_cell(parts):
    for part in reversed(parts):
        value = clean_space(part)

        if value:
            return value.strip('"')

    return ""


def find_city_cell(parts, description_index):
    """
    Finds a separate city column when the pasted row uses one.

    In the user's format, city is usually embedded in "City: description".
    In the colleague format, city is usually the non-empty cell before the
    description.
    """

    for index in range(description_index - 1, -1, -1):
        value = clean_space(parts[index]).strip('"')

        if not value:
            continue

        if looks_like_day(value) or looks_like_known_type(value) or looks_like_date(value):
            continue

        if value.isdigit():
            continue

        # A city cell should be short. Avoid accidentally capturing a long
        # description as the city.
        if len(value) <= 35:
            return value

    return ""


def get_description_index(parts):
    for index in range(len(parts) - 1, -1, -1):
        if clean_space(parts[index]):
            return index

    return -1


def make_row_id(day, item_type, start_date, end_date, description):
    source = "|".join([
        day.strip().lower(),
        item_type.strip().lower(),
        start_date.strip().lower(),
        end_date.strip().lower(),
        description.strip().lower(),
    ])

    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def extract_time_from_description(main_text):
    standard_time = extract_detail(main_text, "Time")

    if standard_time:
        return standard_time

    # Pipe format examples:
    # "Title | 20:00 | 5 Hrs | ..."
    # "Title | 8-10 AM (Anytime) | 7 Hrs | ..."
    pipe_parts = [clean_space(part) for part in main_text.split("|")]

    for part in pipe_parts[1:3]:
        lower = part.lower()
        if re.search(r"\d{1,2}(:\d{2})?\s*(am|pm)?", lower) and "hr" not in lower:
            return part

    # Dash format without label: "Flight | Tromso to Bergen | Self Arranged"
    match = re.search(r"\b(\d{1,2}[:.]\d{2}\s*(?:am|pm)?\s*[-–]\s*\d{1,2}[:.]\d{2}\s*(?:am|pm)?)\b", main_text, flags=re.IGNORECASE)
    if match:
        return clean_space(match.group(1).replace(".", ":"))

    return ""


def extract_meeting_point_from_description(main_text):
    standard_meeting = extract_detail(main_text, "Meeting point")

    if standard_meeting:
        return standard_meeting

    section = extract_between_markers(
        main_text,
        [
            r"pick\s*up\s*/\s*meeting\s*point",
            r"pickup\s*/\s*meeting\s*point",
            r"meeting\s*point\s*:",
            r"pick\s*up\s*:",
        ],
        [
            r"\boverview\b",
            r"\bwhat'?s included\b",
            r"\bwhat’s included\b",
            r"\bwhat to expect\b",
            r"\bimportant info\b",
            r"\n\s*\n",
        ],
    )

    return clean_space(section)


def extract_includes_from_description(main_text):
    standard_includes = extract_detail(main_text, "Includes")

    if standard_includes:
        return split_comma_list(standard_includes, protect_compound_phrases=True)

    section = extract_between_markers(
        main_text,
        [
            r"what'?s included\??",
            r"what’s included\??",
            r"\bincludes\??",
        ],
        [
            r"pick\s*up\s*/\s*meeting\s*point",
            r"pickup\s*/\s*meeting\s*point",
            r"\bmeeting\s*point\b",
            r"\boverview\b",
            r"\bwhat to expect\b",
            r"\bimportant info\b",
            r"\bour floating suits\b",
        ],
    )

    if section:
        return split_comma_list(section, protect_compound_phrases=True)

    lower = main_text.lower()
    fallback_includes = []

    if "ticket" in lower and "included" in lower:
        fallback_includes.append("Tickets included")

    if "luggage porter" in lower:
        fallback_includes.append("Luggage porter service included")

    return fallback_includes


def extract_luggage_included(main_text):
    luggage = extract_detail(main_text, "Luggage included")

    if luggage:
        return luggage

    if "luggage" in main_text.lower() and "included" in main_text.lower():
        for part in re.split(r"[-|]", main_text):
            if "luggage" in part.lower() and "included" in part.lower():
                return clean_space(part)

    return ""


def parse_meal_plan(value):
    text = clean_space(value)
    lower = text.lower()

    if not text:
        return ""

    if "breakfast" in lower or "brekafast" in lower:
        if "dinner" in lower:
            return "breakfast and dinner"
        return "breakfast"

    if "half board" in lower:
        return "half board"

    if "full board" in lower:
        return "full board"

    if "dinner" in lower:
        return "dinner"

    return ""


def clean_room_category(value):
    room = clean_space(value)

    room = re.sub(r"^\d+\s*x\s*", "", room, flags=re.IGNORECASE)
    room = room.replace("Doubel", "Double").replace("doubel", "double")

    return clean_space(room)


def parse_hotel_details(row, main_text, night_count_hint=""):
    """
    Parses accommodation details from both supported formats.

    Standard:
    Check in ... for a 2 night stay - Scandic Rovaniemi City - Standard Room - Breakfast included

    Colleague:
    3 Star , Hotel Arthur, 2xNight , 1xStandard Doubel Room, Incl Brekafast
    """

    text = clean_space(main_text)
    lower = text.lower()

    hotel_name = ""
    nights = ""
    room_category = ""
    meal_plan = ""

    if night_count_hint and str(night_count_hint).strip().isdigit():
        nights = str(night_count_hint).strip()

    match = re.search(r"for\s+a\s+(\d+)\s+night", lower)
    if match:
        nights = match.group(1)

    match = re.search(r"(\d+)\s*x\s*night", lower)
    if match and not nights:
        nights = match.group(1)

    # Standard dash format.
    if " - " in text:
        parts = [clean_space(part) for part in text.split(" - ") if clean_space(part)]

        for part in parts:
            part_lower = part.lower()

            if "check in" in part_lower or "night stay" in part_lower:
                continue

            if "breakfast" in part_lower or "meal" in part_lower or "dinner" in part_lower:
                meal_plan = parse_meal_plan(part)
                continue

            if not hotel_name:
                hotel_name = part
            elif not room_category:
                room_category = clean_room_category(part)

    # Comma format.
    if not hotel_name or not room_category:
        comma_parts = [clean_space(part) for part in re.split(r",|\|", text) if clean_space(part)]

        for part in comma_parts:
            part_lower = part.lower()

            if re.search(r"\d+\s*star", part_lower) or re.search(r"\d+\s*x\s*night", part_lower):
                continue

            if "incl" in part_lower or "breakfast" in part_lower or "brekafast" in part_lower or "dinner" in part_lower:
                meal_plan = meal_plan or parse_meal_plan(part)
                continue

            if "room" in part_lower or "igloo" in part_lower or "suite" in part_lower or "cabin" in part_lower:
                room_category = room_category or clean_room_category(part)
                continue

            if not hotel_name:
                hotel_name = part

    # If hotel name is missing in the text, avoid using the whole raw line.
    if hotel_name and any(marker in hotel_name.lower() for marker in ["check in", "night stay", "incl"]):
        hotel_name = ""

    return {
        "hotel_name": hotel_name,
        "hotel_nights": nights,
        "room_category": room_category,
        "meal_plan": meal_plan,
    }


def parse_itinerary(raw_text):
    rows = []
    seen_row_ids = set()
    current_day = ""

    for line_number, raw_line in enumerate(preprocess_raw_rows(raw_text), start=1):
        if not raw_line.strip():
            continue

        parts = raw_line.rstrip("\n").split("\t")

        if not any(part.strip() for part in parts):
            continue

        day_index = find_day_index(parts)

        if day_index is not None:
            current_day = clean_space(parts[day_index])
        elif not current_day:
            continue

        type_index = day_index + 1 if day_index is not None else 1
        item_type = normalize_type(parts[type_index]) if len(parts) > type_index else ""

        if not item_type:
            continue

        description_index = get_description_index(parts)
        description = find_description_cell(parts)

        if not description:
            continue

        night_count_hint = ""
        date_values = []

        for part in parts[type_index + 1:description_index]:
            value = clean_space(part)

            if not value:
                continue

            if not night_count_hint and item_type == "Hotel" and value.isdigit():
                night_count_hint = value
                continue

            if looks_like_date(value):
                date_values.append(value)

        start_date = date_values[0] if len(date_values) >= 1 else ""
        end_date = date_values[1] if len(date_values) >= 2 else ""

        separate_city = find_city_cell(parts, description_index)

        row_id = make_row_id(current_day, item_type, start_date, end_date, description)

        if row_id in seen_row_ids:
            continue

        seen_row_ids.add(row_id)

        row = {
            "raw": clean_space(raw_line),
            "line_number": line_number,
            "row_id": row_id,
            "day": current_day,
            "type": item_type,
            "effective_type": "",
            "start_date": start_date,
            "end_date": end_date,
            "city": "",
            "title": "",
            "details": description,
            "time": "",
            "meeting_point": "",
            "end_point": "",
            "notable_sights": [],
            "includes": [],
            "luggage_included": "",
            "hotel_name": "",
            "hotel_nights": "",
            "room_category": "",
            "meal_plan": "",
        }

        main_text = description.strip().strip('"')

        if separate_city:
            row["city"] = separate_city

            if ":" in main_text:
                possible_city, rest = main_text.split(":", 1)
                if clean_space(possible_city).lower() == clean_space(separate_city).lower():
                    main_text = rest.strip()

        elif ":" in main_text:
            possible_city, rest = main_text.split(":", 1)
            if len(clean_space(possible_city)) <= 35:
                row["city"] = clean_space(possible_city)
                main_text = rest.strip()

        main_text = fix_common_text(main_text)
        row["details"] = fix_common_text(description)
        row["city"] = fix_common_text(row.get("city", ""))
        row["title"] = clean_title(main_text)
        row["original_title"] = row["title"]
        row["time"] = extract_time_from_description(main_text)
        row["meeting_point"] = extract_meeting_point_from_description(main_text)
        row["end_point"] = extract_detail(main_text, "End point")
        row["notable_sights"] = split_comma_list(extract_detail(main_text, "Notable Sights"))
        row["includes"] = extract_includes_from_description(main_text)
        row["luggage_included"] = extract_luggage_included(main_text)

        if normalize_type(item_type) == "Hotel":
            hotel_details = parse_hotel_details(row, main_text, night_count_hint=night_count_hint)
            row.update(hotel_details)

        row["effective_type"] = detect_effective_type(
            row["type"],
            row["title"],
            row["details"],
        )

        row = standardize_row_text(row)

        rows.append(row)

    return rows
