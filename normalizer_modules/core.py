"""
normalizer.py

Post-parser normalization for itinerary rows.

This layer keeps the parser focused on extraction and the generator focused on
rendering. It makes parsed rows safer and more client-facing before they reach
preview/PDF generation.
"""

from __future__ import annotations

import copy
import re
from collections import Counter

import diagnostics
from place_aliases import canonicalize_place_name, is_likely_service_text, is_known_place
from text_polish import polish_client_text, polish_hotel_name, polish_inclusion_items, polish_inclusion_item, polish_title, expand_time_with_duration, format_duration_display


TRANSPORT_TYPES = {"Transport", "Train", "Flight", "Cruise", "Ferry"}


def clean_space(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def get_row_type(row: dict) -> str:
    return row.get("effective_type") or row.get("type", "")


def text_blob(row: dict) -> str:
    parts = [
        row.get("city", ""),
        row.get("title", ""),
        row.get("original_title", ""),
        row.get("details", ""),
        " ".join(row.get("includes", []) or []),
    ]
    return clean_space(" ".join(str(part or "") for part in parts))


def _lower_key(value: str) -> str:
    return re.sub(r"[^a-z0-9åäöøæéü -]+", " ", str(value or "").lower()).strip()


def looks_like_departure_text(value: str) -> bool:
    lower = _lower_key(value)
    markers = [
        "check out",
        "transfer to the airport",
        "drop at the airport",
        "return flight",
        "bound for home",
        "departure home",
        "onward flight",
        "packed breakfast",
    ]
    return sum(1 for marker in markers if marker in lower) >= 2 or ("return flight" in lower and "airport" in lower)


def _normalize_single_room_category(value: str) -> str:
    room = polish_client_text(value)
    room = re.sub(r"^\s*\d+\s*x\s*", "", room, flags=re.IGNORECASE)
    room = re.sub(r"\bTirple\b", "Triple", room, flags=re.IGNORECASE)
    room = re.sub(r"\bStandard\s+room\b", "Standard Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bStandard\s+Double\s+room\b", "Standard Double Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bStandard\s+Double\s+Room\b", "Standard Double Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bTriple\s+room\b", "Triple Room", room, flags=re.IGNORECASE)
    room = re.sub(r"\bPanorama\s+suite\b", "Panorama Suite", room, flags=re.IGNORECASE)
    room = re.sub(r"\bSmall\s+Glass\s+Igloo\b", "Small Glass Igloo", room, flags=re.IGNORECASE)
    room = re.sub(r"\bWest\s+or\s+east\s+Village\b", "West or East Village", room, flags=re.IGNORECASE)
    room = re.sub(r"\bSmall Glass Igloo\s+(West or East Village)\b", r"Small Glass Igloo, \1", room, flags=re.IGNORECASE)
    return clean_space(room.strip(" ,-"))


def normalize_room_category(value: str) -> str:
    room = polish_client_text(value)
    room = re.sub(r"\bTirple\b", "Triple", room, flags=re.IGNORECASE)
    room = re.sub(r"(?<=\D)(\d+\s*x\s*)", r" \1", room, flags=re.IGNORECASE)
    if re.search(r"\bnight'?s?\b", room, flags=re.IGNORECASE):
        return ""

    multi_room_pattern = re.compile(
        r"(?:\d+\s*x\s*)?(.+?(?:Room|Suite|Cabin|Igloo))(?=\s+\d+\s*x|$)",
        flags=re.IGNORECASE,
    )
    matches = [_normalize_single_room_category(match.group(1)) for match in multi_room_pattern.finditer(room)]
    matches = [match for match in matches if match]
    if matches:
        deduped = []
        for match in matches:
            if match not in deduped:
                deduped.append(match)
        return " and ".join(deduped)

    return _normalize_single_room_category(room)


def normalize_meal_plan(value: str, source_text: str = "") -> str:
    text = f"{value} {source_text}".lower()
    if any(marker in text for marker in ["without breakfast", "without brekafast", "no breakfast", "breakfast not"]):
        return "without breakfast"
    if "breakfast" in text or "brekafast" in text or "breekfast" in text:
        if "dinner" in text:
            return "breakfast and dinner"
        return "breakfast"
    if "dinner" in text:
        return "dinner"
    return polish_client_text(value)


def extract_star_level(value: str) -> str:
    text = str(value or "")
    match = re.search(r"\b([2-5])\s*[- ]?star\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def is_placeholder_hotel_name(name: str, city: str = "") -> bool:
    text = clean_space(name)
    if not text:
        return True
    lower = text.lower()
    city_lower = clean_space(city).lower()
    if city_lower and lower in {city_lower, canonicalize_place_name(city).lower()}:
        return True
    if re.search(r"\b\d\s*[- ]?star\b", lower):
        return True
    if re.search(r"\b\d+\s*x?\s*night", lower):
        return True
    if any(marker in lower for marker in ["standard room", "standard double room", "incl breakfast", "incl brekafast", "breakfast", "room category"]):
        return True
    if lower in {"hotel", "accommodation", "or similar", "similar"}:
        return True
    return False


def clean_hotel_name_from_source(row: dict) -> str:
    source = clean_space(row.get("details", ""))
    city = clean_space(row.get("city", ""))
    source = re.sub(r"\([^)]*supplement[^)]*\)", "", source, flags=re.IGNORECASE)
    source = re.sub(r"\([^)]*upgrade[^)]*\)", "", source, flags=re.IGNORECASE)
    parts = [clean_space(part) for part in re.split(r"\s+-\s+|,|\|", source) if clean_space(part)]
    candidates = []
    hotel_brand_prefixes = ("scandic", "radisson", "comfort", "quality", "clarion", "thon", "moxy", "grand", "hotel", "santa", "kakslauttanen")

    for part in parts:
        part_clean = polish_hotel_name(part)
        lower = part_clean.lower()
        if city and lower == city.lower():
            continue
        if re.search(r"\b\d\s*[- ]?star\b", lower):
            continue
        if re.search(r"\b\d+\s*x?\s*night", lower):
            # Some weak inputs use either "2 Night's Hotel Scandic Kemi" or
            # "Hotel Aakenus 2xNight" in the same comma fragment.
            trailing = re.sub(r"^\s*\d+\s*(?:x\s*)?night'?s?\s*", "", part_clean, flags=re.IGNORECASE).strip(" ,-:")
            trailing = re.sub(r"\s*\d+\s*(?:x\s*)?night'?s?\s*$", "", trailing, flags=re.IGNORECASE).strip(" ,-:")
            if trailing:
                part_clean = trailing
                lower = part_clean.lower()
            else:
                continue
        if any(marker in lower for marker in ["standard", "double room", "breakfast", "brekafast", "dinner"]):
            continue
        if lower.startswith("hotel ") and any(lower.startswith(f"hotel {brand}") for brand in ["scandic", "radisson", "comfort", "quality", "clarion", "thon", "moxy", "grand"]):
            part_clean = part_clean[6:].strip()
        if lower.startswith(hotel_brand_prefixes) or len(part_clean.split()) >= 2:
            candidates.append(part_clean)

    return polish_hotel_name(candidates[0]) if candidates else ""


def normalize_hotel_row(row: dict) -> dict:
    source = clean_space(row.get("details", ""))
    city = clean_space(row.get("city", ""))
    star = extract_star_level(source)

    name = polish_hotel_name(row.get("hotel_name", ""))
    if is_placeholder_hotel_name(name, city):
        detected = clean_hotel_name_from_source(row)
        if detected and not is_placeholder_hotel_name(detected, city):
            name = detected
        elif star:
            name = f"{star}-star hotel"
        else:
            name = "Centrally located hotel"

    room = normalize_room_category(row.get("room_category", ""))
    if not room:
        # Look for a room fragment in the original source.
        room_match = re.search(r"(?:\d+\s*x\s*)?((?:standard|superior|deluxe|small glass|glass|double|single|twin)[^,|;-]*(?:room|igloo|suite|cabin)?)", source, flags=re.IGNORECASE)
        if room_match:
            room = normalize_room_category(room_match.group(1))
    if not room:
        room = "Standard Double Room"

    nights = clean_space(row.get("hotel_nights", ""))
    if not nights:
        night_match = re.search(r"\b(\d+)\s*(?:x\s*)?night", source, flags=re.IGNORECASE)
        if night_match:
            nights = night_match.group(1)

    meal = normalize_meal_plan(row.get("meal_plan", ""), source)

    # Strip trailing city suffix that bleeds into hotel names
    # e.g. "Scandic Rovaniemi city" → "Scandic Rovaniemi"
    if city and name.lower().endswith(" city"):
        trimmed = name[:-5].strip()
        if trimmed:
            name = trimmed

    name = re.sub(r"\bSariselka\b", "Saariselkä", name, flags=re.IGNORECASE)
    row["hotel_name"] = name
    row["title"] = name
    row["room_category"] = room
    row["hotel_nights"] = nights
    row["meal_plan"] = meal
    return row


def normalize_activity_title(row: dict) -> str:
    source = text_blob(row)
    lower = source.lower()
    city = canonicalize_place_name(row.get("city", ""))

    if looks_like_departure_text(source):
        return f"Departure from {city}" if city else "Departure"
    if ("aurora" in lower or "northern light" in lower) and "reindeer" in lower and ("hunt" in lower or "hunting" in lower or "chase" in lower):
        return "Northern Lights Hunt by Reindeer"
    if "tallin" in lower or "tallinn" in lower:
        if "old town" in lower and "guided" in lower and not any(marker in lower for marker in ["helsinki", "ferry", "cruise", "star class", "port"]):
            return "Tallinn Old Town Guided Tour"
        return "Day Trip to Tallinn"
    if "fjellheisen" in lower or ("round trip ticket" in lower and "trom" in lower) or "cable car" in lower:
        return "Fjellheisen Cable Car"
    if "essential oslo" in lower or ("oslo" in lower and "city center guided walking tour" in lower):
        return "Oslo City Center Walking Tour"
    if "must-see bergen" in lower or ("bergen" in lower and "foot and boat" in lower):
        return "Bergen Walking & Boat Tour"
    if "santa claus village" in lower and ("reindeer" in lower or "safari" in lower):
        if "snowmobile" in lower or "snowmobiles" in lower:
            return "Santa Claus Village by Snowmobile & Reindeer Sleigh"
        if "husky" in lower:
            return "City Highlights, Santa Claus Village & Husky-Reindeer Safari"
        return "Santa Claus Village & Reindeer Visit"
    if "guided city tour" in lower and "narvik" in lower:
        return "Narvik Guided City Tour"
    if "ice bar" in lower and ("kiruna" in lower or "jukkasjärvi" in lower or "gällivare" in lower or "gallivare" in lower):
        return "Icehotel, Kiruna & Gällivare Touring Day"
    if "trom" in lower and "city sightseeing" in lower:
        if "aurora" in lower or "northern light" in lower:
            return "Tromsø City Sightseeing & Northern Lights Chase"
        return "Tromsø City Sightseeing"
    if "arctic wildlife" in lower and "ranua" in lower:
        return "Arctic Wildlife Adventure to Ranua Park"
    if "guided walking tour of helsinki" in lower or ("helsinki" in lower and "guided walking tour" in lower):
        return "Helsinki Guided Walking Tour"
    if "lofoten" in lower and "trollfjord" in lower:
        return "Lofoten Day Tour & Trollfjord Cruise"
    if "hop" in lower and "off" in lower and "bus" in lower:
        if "bergen" in lower:
            return "Bergen Hop-On Hop-Off Bus Ticket"
        if "copenhagen" in lower:
            return "Copenhagen Hop-On Hop-Off Bus Ticket"
        return "Hop-On Hop-Off Bus Ticket"

    # Fix "Private" or time-string titles from pipe-formatted rows
    raw_title = row.get("title", "").strip()
    if raw_title.lower() in {"private", "private day tour", ""} and "|" in row.get("details", ""):
        detail_parts = [p.strip() for p in row.get("details", "").split("|")]
        for part in detail_parts[1:]:
            part_clean = re.sub(r"^\d+\s*(am|pm|hrs?|hour)", "", part, flags=re.IGNORECASE).strip(" -:")
            part_clean = re.sub(r"\b\d+\s*hrs?\b", "", part_clean, flags=re.IGNORECASE).strip(" -:")
            if len(part_clean) > 5 and not re.match(r"^\d", part_clean):
                return polish_title(part_clean)

    if re.match(r"^from\s+\d", raw_title.lower()) or re.match(r"^\d+\s*(am|pm)\s+to\s+\d", raw_title.lower()):
        if "sightseeing" in lower or "private" in lower:
            return f"Private Sightseeing{' in ' + city if city else ''}"
        return f"Guided Experience{' in ' + city if city else ''}"

    title = polish_title(row.get("title", ""))
    if len(title) > 90 or title.count(".") >= 2:
        first = re.split(r"[.|]", title, maxsplit=1)[0].strip(" ,-:")
        if len(first) <= 70 and first:
            title = first
        elif city:
            title = f"Guided experience in {city}"
        else:
            title = "Guided experience"
    return polish_title(title)


def normalize_inclusion_value(value: str) -> str:
    item = polish_inclusion_item(value)
    item = re.sub(r"\bcomfortable\s+mini\s*bus\b", "Comfortable minibus", item, flags=re.IGNORECASE)
    item = re.sub(r"\bbest\s+aurora\s+spots\b", "Best available aurora viewing spots", item, flags=re.IGNORECASE)
    item = re.sub(r"\bexpert\s+guide\b", "Expert guide", item, flags=re.IGNORECASE)
    item = re.sub(r"\bhot\s+beverages?\s+and\s+(?:a\s+)?little\s+snack\b", "Hot beverages and a light snack", item, flags=re.IGNORECASE)
    item = re.sub(r"\bcoffee\s+and\s+waffles\s*/\s*cookies\b", "Coffee and waffles or cookies", item, flags=re.IGNORECASE)
    item = re.sub(r"\bhot\s+drinks?\s+and\s+snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies", item, flags=re.IGNORECASE)
    item = re.sub(r"\bauthorized\s+english\s*-\s*speaker\s+guide\b", "Authorised English-speaking guide", item, flags=re.IGNORECASE)
    item = re.sub(r"\bbaby\s+seats?\s+[åa]re\s+provided\s+if\s+needed\b", "Baby seats are provided if needed", item, flags=re.IGNORECASE)
    item = re.sub(r"\bhot\s+drink\s+and\s+biscuits?\s+[åa]re\s+provided\b", "Hot drink and biscuits are provided", item, flags=re.IGNORECASE)
    item = re.sub(r"\bwarm\s+drink\s+and\s+cookies\s+[åa]re\s+included\b", "Warm drink and cookies are included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bfood\s+and\s+drinks\s+[å]re\b", "Food and drinks are included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bfood\s+and\s+drinks\s+are\b(?!\s+included)", "Food and drinks are included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bwarm\s+drinks?\s*&\s*light\s+snacks?\s*/\s*sausage\b", "Warm drinks and light snacks or sausage", item, flags=re.IGNORECASE)
    item = re.sub(r"\bsnacks?\s*&\s*hot\s+drinks?\b", "Snacks and hot drinks", item, flags=re.IGNORECASE)
    item = re.sub(r"\blegends?\s*&\s*explanation\b", "legends and explanations", item, flags=re.IGNORECASE)
    item = re.sub(r"\bMagic scenery and Lapland magic\b", "Scenic Lapland wilderness experience", item, flags=re.IGNORECASE)
    item = re.sub(r"\bHotel Pick-up/drop-off\b", "Hotel pick-up/drop-off", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTour guiding\b", "Local guide service", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTour transportation\b", "Transport during the tour", item, flags=re.IGNORECASE)
    item = re.sub(r'^Include\s*[,":]?\s*', "", item, flags=re.IGNORECASE)
    if re.fullmatch(r"Overalls", item, flags=re.IGNORECASE):
        item = "Winter equipment provided"
    item = re.sub(r"\bThermal\s+Winter\s+overalls\b", "Thermal overalls", item, flags=re.IGNORECASE)
    item = re.sub(r"\bWinter clothes\s*\(Winter overalls and boots\)", "Winter clothes (overalls and boots)", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTransfer from and to\b", "Transfer to and from", item, flags=re.IGNORECASE)
    item = re.sub(r"\bboots\b", "boots", item, flags=re.IGNORECASE)
    item = re.sub(r"\bgloves\b", "gloves", item, flags=re.IGNORECASE)
    item = re.sub(r"\bbalaclava\s*&\s*helmet\b", "balaclava and helmet", item, flags=re.IGNORECASE)
    item = re.sub(r"\bWinter equipment\b", "Winter equipment", item, flags=re.IGNORECASE)
    item = re.sub(r"\bComfortable coach transport with toilet\b", "Comfortable coach transport with onboard toilet", item, flags=re.IGNORECASE)
    item = re.sub(r"\bNorthern Lights instructions video on coach\b", "Northern Lights briefing on board", item, flags=re.IGNORECASE)
    item = re.sub(r"\b([Hh])elp with camera settings and nature photos,\s*Small-group experience", r"Help with camera settings and nature photos, Small-group experience", item)
    item = re.sub(r"(?:\s+included){2,}$", " included", item, flags=re.IGNORECASE)
    return polish_inclusion_item(item)


def split_and_merge_inclusions(items: list[str]) -> list[str]:
    cleaned = []
    raw_items = [normalize_inclusion_value(item) for item in items or [] if normalize_inclusion_value(item)]
    index = 0
    while index < len(raw_items):
        item = re.split(r"\s+-\s+(?:Description|Overview)\s*:", raw_items[index], maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
        if not item:
            index += 1
            continue
        lower = item.lower().strip(" ,.:")
        next_item = raw_items[index + 1] if index + 1 < len(raw_items) else ""
        next_lower = next_item.lower().strip(" ,.:")

        if lower == "english" and next_lower in {"french speaking guide", "french-speaking guide"}:
            cleaned.append("English- and French-speaking guide")
            index += 2
            continue
        if lower in {"winter overalls", "winter equipment provided"} and next_lower == "boots":
            following = [raw_items[i].lower().strip(" ,.:&") for i in range(index + 2, min(index + 5, len(raw_items)))]
            if "gloves" in following or any("balaclava" in value for value in following):
                cleaned.append("Winter equipment provided")
                index += 1
                while index < len(raw_items) and raw_items[index].lower().strip(" ,.:&") in {"boots", "gloves", "balaclava and helmet"}:
                    index += 1
                continue
        if lower == "stories" and next_lower in {"legends and explanations", "legends & explanation"}:
            cleaned.append("Stories, legends and explanations")
            index += 2
            continue

        # Split a common comma-merged bullet from photo-tour rows.
        if ", small-group experience" in lower:
            first, second = re.split(r",\s*(?=Small-group experience)", item, maxsplit=1, flags=re.IGNORECASE)
            for part in [first, second]:
                part = normalize_inclusion_value(part)
                if part and part not in cleaned:
                    cleaned.append(part)
            index += 1
            continue

        if "guided hike in korouoma canyon," in lower:
            first = re.split(r",\s*(?=Small groups|small groups)", item, maxsplit=1)[0].strip()
            item = normalize_inclusion_value(first)
            lower = item.lower().strip(" ,.:")

        if lower in {"small groups", "small groups (max 8 guests)", "max 8 guests"}:
            index += 1
            continue

        if item and item not in cleaned:
            cleaned.append(item)
        index += 1

    return polish_inclusion_items(cleaned)



def expand_single_start_time_with_duration(time_value: str, duration_value: str) -> str:
    """Return a start-end time range when time + duration are reliable."""
    return expand_time_with_duration(time_value, duration_value)


def normalize_time_range_fields(row: dict) -> dict:
    """Normalize activity time display before rendering/exporting."""
    if get_row_type(row) != "Activity":
        return row
    row["time"] = expand_single_start_time_with_duration(row.get("time", ""), row.get("duration", ""))
    return row

def normalize_transport_title(row: dict) -> dict:
    title = polish_title(row.get("title", ""))
    details = polish_client_text(row.get("details", ""))
    full = f"{title} {details}".lower()
    if "tallin" in full:
        row["title"] = re.sub("Tallin", "Tallinn", title, flags=re.IGNORECASE)
    if "rovaneimi" in full:
        row["title"] = re.sub("Rovaneimi", "Rovaniemi", title, flags=re.IGNORECASE)
    if row.get("type") == "Cruise" or "overnight cruise" in full:
        if "stockholm" in full:
            row["title"] = "Cruise to Stockholm"
            row["city"] = "Stockholm" if row.get("city", "").lower() in {"helsinki", ""} else row.get("city")
    return row


def warn_suspicious_city(row: dict) -> None:
    city = clean_space(row.get("city", ""))
    if not city:
        return
    lower = city.lower()
    if is_likely_service_text(city) or any(marker in lower for marker in ["ticket", "option", "sightseeing", "private tour", "hop on", "hop-off", "cancel"]):
        diagnostics.warn(
            "suspicious_city",
            f"Suspicious city value '{city}' on {row.get('day', 'Unknown day')} — check source columns.",
            raw_value=row.get("raw", city),
        )
        row["city"] = ""
        return
    if city and not is_known_place(city) and len(city) > 18:
        diagnostics.warn(
            "unrecognised_city",
            f"City '{city}' on {row.get('day', 'Unknown day')} is not in the known place list — verify it is correct.",
            raw_value=row.get("raw", city),
        )


def normalize_row(row: dict) -> dict:
    row = copy.deepcopy(row)

    for key in ["city", "title", "original_title", "details", "meeting_point", "end_point", "luggage_included"]:
        if row.get(key):
            row[key] = polish_client_text(row[key])

    if row.get("duration"):
        duration_text = row["duration"]
        if re.search(r"\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*hours?", duration_text, flags=re.IGNORECASE):
            row["duration"] = duration_text.replace("-", "–")
        else:
            row["duration"] = format_duration_display(duration_text)

    row["city"] = canonicalize_place_name(row.get("city", ""))
    warn_suspicious_city(row)

    row_type = get_row_type(row)
    full = text_blob(row)

    if looks_like_departure_text(full):
        row["effective_type"] = "Departure"
        row["type"] = row.get("type") or "Departure"
        city = canonicalize_place_name(row.get("city", ""))
        row["title"] = f"Departure from {city}" if city else "Departure"
        return row

    if row_type == "Hotel":
        return normalize_hotel_row(row)

    if row_type == "Activity":
        title = normalize_activity_title(row)
        row["title"] = title
        row["original_title"] = row.get("original_title") or title
        if row.get("time"):
            row["display_time"] = expand_time_with_duration(row.get("time", ""), row.get("duration", ""))
        else:
            row["display_time"] = ""
        row["display_duration"] = format_duration_display(row.get("duration", "")) if row.get("duration") else ""

    if row_type in TRANSPORT_TYPES or row_type == "Transfer":
        row = normalize_transport_title(row)

    if isinstance(row.get("includes"), list):
        row["includes"] = split_and_merge_inclusions(row.get("includes", []))
    if isinstance(row.get("notable_sights"), list):
        row["notable_sights"] = split_and_merge_inclusions(row.get("notable_sights", []))

    row = normalize_time_range_fields(row)
    return row


def add_repeated_activity_context(rows: list[dict]) -> list[dict]:
    titles = [row.get("title", "") for row in rows if get_row_type(row) == "Activity" and row.get("title")]
    counts = Counter(titles)
    updated = []
    for row in rows:
        row = copy.deepcopy(row)
        if get_row_type(row) == "Activity" and counts.get(row.get("title", ""), 0) > 1:
            city = canonicalize_place_name(row.get("city", ""))
            title = row.get("title", "")
            if city and f" in {city}" not in title and title.lower().startswith("northern lights"):
                row["inclusion_title"] = f"{title} in {city}"
        updated.append(row)
    return updated




def _day_number_value(value: str) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def _next_main_city(rows: list[dict], current_index: int) -> str:
    current_day = _day_number_value(rows[current_index].get("day", ""))
    for later in rows[current_index + 1:]:
        later_day = _day_number_value(later.get("day", ""))
        if later_day and current_day and later_day <= current_day:
            continue
        city = canonicalize_place_name(later.get("city", ""))
        if city and get_row_type(later) in {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Departure"}:
            return city
    return ""


def apply_contextual_travel_corrections(rows: list[dict]) -> list[dict]:
    updated = [copy.deepcopy(row) for row in rows or []]
    previous_overnight_destination = ""

    for index, row in enumerate(updated):
        row_type = get_row_type(row)
        full = text_blob(row).lower()

        if row_type == "Train" and "overnight" in full and "train" in full:
            next_city = _next_main_city(updated, index)
            row_city = canonicalize_place_name(row.get("city", ""))
            if next_city and next_city != row_city:
                row["title"] = f"Overnight Train to {next_city}"
                previous_overnight_destination = next_city
            else:
                previous_overnight_destination = row_city or next_city
            continue

        if row_type == "Transfer":
            title_lower = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
            city = canonicalize_place_name(row.get("city", ""))
            day = row.get("day", "")
            same_day_has_hotel = any(
                other is not row and other.get("day") == day and get_row_type(other) == "Hotel"
                for other in updated
            )
            if (
                "hotel to station" in title_lower
                and previous_overnight_destination
                and city == previous_overnight_destination
                and same_day_has_hotel
            ):
                row["title"] = "Private transfer from the station to your hotel"
                row["original_title"] = row.get("original_title") or "Private Hotel to Station"

    return updated

def normalize_itinerary_rows(rows: list[dict]) -> list[dict]:
    normalized = [normalize_row(row) for row in rows or []]
    normalized = apply_contextual_travel_corrections(normalized)
    normalized = add_repeated_activity_context(normalized)
    return normalized
