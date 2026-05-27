from itinerary_generation.common import (
    get_day_count,
    get_day_number,
    get_primary_city,
    get_row_type,
    get_unique_cities,
    has_self_drive_markers,
    is_valid_destination_city,
    main_rows_only,
)
from place_aliases import canonicalize_place_name
from itinerary_generation.transport import (
    has_glass_igloo_or_arctic_resort,
    has_norway_in_a_nutshell,
)


def create_trip_glance(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    cities = get_unique_cities(parsed_rows)
    day_count = get_day_count(grouped_days)
    nights = max(day_count - 1, 0)

    row_cities = [
        canonicalize_place_name(row.get("city", ""))
        for row in parsed_rows
        if is_valid_destination_city(canonicalize_place_name(row.get("city", "")))
    ]
    start_city = row_cities[0] if row_cities else (cities[0] if cities else "TBA")
    end_city = row_cities[-1] if row_cities else (cities[-1] if cities else "TBA")
    destinations = " · ".join(cities) if cities else "TBA"

    hotel_rows = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    activity_rows = [row for row in parsed_rows if get_row_type(row) == "Activity"]
    transfer_rows = [row for row in parsed_rows if get_row_type(row) == "Transfer"]

    has_breakfast = any(
        "breakfast" in row.get("details", "").lower()
        or "brekafast" in row.get("details", "").lower()
        for row in hotel_rows
    )

    has_private_transfer = any(
        "private" in row.get("details", "").lower()
        for row in transfer_rows
    )

    has_self_transfer = any(
        "self transfer" in row.get("details", "").lower()
        for row in transfer_rows
    )

    travel_style_parts = []

    if has_self_drive_markers(parsed_rows):
        if hotel_rows:
            travel_style_parts.append("curated stays")
        travel_style_parts.append("scenic self-drive routes")
        if activity_rows:
            travel_style_parts.append("selected experiences")
        travel_style = "Premium self-drive journey with " + ", ".join(travel_style_parts)
    else:
        if has_private_transfer:
            travel_style_parts.append("private transfers")

        if has_self_transfer:
            travel_style_parts.append("self-guided transfers")

        if activity_rows:
            travel_style_parts.append("guided experiences")

        if hotel_rows:
            travel_style_parts.append("arranged accommodation")

        if travel_style_parts:
            travel_style = "Premium independent journey with " + ", ".join(travel_style_parts)
        else:
            travel_style = "Independent journey with arranged services"

    hotel_level = "Hotels as specified in the itinerary"

    if hotel_rows:
        hotel_level = "Accommodation as listed"

        if has_breakfast:
            hotel_level += ", breakfast included where specified"

    night_word = "night" if nights == 1 else "nights"

    return {
        "Duration": f"{day_count} days / {nights} {night_word}",
        "Start": start_city,
        "End": end_city,
        "Destinations": destinations,
        "Travel Style": travel_style,
        "Hotel Level": hotel_level,
    }


def _has(text, *markers):
    return any(marker in text for marker in markers)


def _add_theme(items, theme):
    if theme and theme not in items:
        items.append(theme)


def _title_case_arc(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return "Time to explore at your own pace"
    return text[:1].upper() + text[1:]


def _compact_arc_phrase(candidates):
    """Pick a short Journey Arc phrase suitable for one table row."""
    for phrase in candidates:
        phrase = _title_case_arc(phrase)
        if len(phrase) <= 48:
            return phrase
    phrase = _title_case_arc(candidates[0] if candidates else "Time to explore at your own pace")
    return phrase[:45].rstrip(" ,") + "..." if len(phrase) > 48 else phrase


def describe_city_experience(rows):
    text = " ".join(
        " ".join([
            str(row.get("city", "")),
            str(row.get("title", "")),
            str(row.get("original_title", "")),
            str(row.get("details", "")),
            " ".join(row.get("includes", []) or []),
        ]).lower()
        for row in rows
    )
    row_types = {get_row_type(row) for row in rows}

    if has_glass_igloo_or_arctic_resort(rows):
        return "Arctic resort and glass igloo stay"

    has_arrival = any(get_row_type(row) == "Arrival" for row in rows)
    has_departure = any(get_row_type(row) == "Departure" for row in rows)
    has_hotel_only = row_types == {"Hotel"}
    travel_only_with_hotel = row_types.issubset({"Hotel", "Transfer", "Flight", "Train", "Transport", "Cruise", "Ferry"}) and any(get_row_type(row) == "Hotel" for row in rows)

    has_nutshell = has_norway_in_a_nutshell(rows) or _has(text, "flåm", "flam", "nærøyfjord", "naeroyfjord", "bergen railway", "flåm railway", "flam railway")
    has_self_drive = _has(text, "self-drive", "self drive", "rental vehicle", "rental suv", "route suggested", "scenic drive", "return drive", "road trip")
    has_lagoon = _has(text, "blue lagoon", "sky lagoon", "spa", "wellness", "7-step", "ritual")
    has_silfra = _has(text, "silfra", "snork")
    has_golden = _has(text, "golden circle", "kerið", "kerid")
    has_south = _has(text, "south coast", "diamond beach", "black sand")
    has_adventure = _has(text, "atv", "quad", "glacier", "hike", "hiking", "crampon")
    has_whale = _has(text, "whale", "wildlife", "rib boat")
    has_fjord = _has(text, "fjord", "trollfjord", "cruise", "catamaran", "silent electric ship") or ("boat" in text and not _has(text, "stockholm", "vasa", "old town"))
    has_food = _has(text, "food", "tasting", "smørrebrød", "secret food", "fish soup", "lunch", "dinner", "meal")
    has_tallinn = _has(text, "tallinn")
    has_city = _has(text, "vasa", "old town", "museum", "walking tour", "city walk", "must-see", "guided visit", "helsinki guide", "senate square", "senate squate")
    has_nature = _has(text, "forest tower", "forgotten giants", "nature hike", "haukland", "henningsvær", "photo tour", "arctic landscape")
    has_aurora = _has(text, "northern light", "aurora")
    has_leisure = _has(text, "leisure", "spend time at leisure", "free time", "explore")
    has_reindeer_sami = _has(text, "reindeer", "sámi", "sami", "husky", "santa claus village")
    has_cable = _has(text, "fjellheisen", "cable car", "funicular", "fløibanen", "floibanen")
    has_flight = _has(text, "flight")

    candidates = []

    if _has(text, "spend time at leisure onboard the cruise") and row_types == {"Cruise"}:
        candidates.append("Coastal cruise at leisure")
    if _has(text, "cruise to bergen") and _has(text, "kirkenes"):
        candidates.append("Cruise departure towards Bergen")
    if _has(text, "cruise arrival to bergen", "arrival to bergen"):
        candidates.append("Cruise arrival and Bergen stay")

    if has_tallinn:
        candidates.append("Tallinn day trip and onward train")
    if has_nutshell:
        candidates.append("Norway in a Nutshell and scenic rail")
    if has_golden and has_silfra:
        candidates.append("Golden Circle and Silfra snorkelling")
    elif has_silfra:
        candidates.append("Silfra snorkelling")
    elif has_golden:
        candidates.append("Golden Circle route")

    if has_lagoon and has_self_drive and has_whale:
        candidates.append("Lagoon, self-drive route and whale watching")
    elif has_lagoon and has_self_drive:
        candidates.append("Lagoon and scenic self-drive route")
    elif has_lagoon:
        candidates.append("Lagoon and wellness")

    if has_south and has_adventure:
        candidates.append("South Coast scenery and soft adventure")
    elif has_south:
        candidates.append("South Coast scenery")

    if has_reindeer_sami and has_aurora:
        if "santa claus village" in text:
            candidates.append("Aurora, Santa Village and Arctic experiences")
        elif has_fjord or has_nature:
            candidates.append("Sámi culture, fjords and northern lights")
        else:
            candidates.append("Aurora, Sámi culture and Arctic experiences")
    elif has_reindeer_sami:
        candidates.append("Sámi culture and Arctic experiences")
    elif has_aurora and has_whale:
        candidates.append("Wildlife, aurora and Arctic coast")
    elif has_aurora:
        candidates.append("Northern Lights experiences")

    if _has(text, "lofoten", "henningsvær", "haukland", "trollfjord"):
        candidates.append("Lofoten scenery and Trollfjord cruising")
    elif has_fjord and has_cable:
        if _has(text, "arctic", "tromsø", "tromso", "alta"):
            candidates.append("Arctic fjords and cable car views")
        else:
            candidates.append("Fjord views and funicular")
    elif has_fjord and has_whale:
        candidates.append("Coastal wildlife and fjord scenery")
    elif has_fjord:
        candidates.append("Fjord scenery and coastal cruising")

    if has_city and _has(text, "vasa", "old town", "stockholm"):
        candidates.append("Old Town, Vasa Museum and city discovery")
    elif has_city and has_arrival:
        candidates.append("Arrival and guided city discovery")
    elif has_city:
        candidates.append("Guided city discovery")

    if has_food and not any("food" in c.lower() for c in candidates):
        candidates.append("Local food culture")
    if has_nature and not any(marker in " ".join(candidates).lower() for marker in ["nature", "lofoten", "arctic fjords", "south coast"]):
        candidates.append("Scenic nature experiences")
    if has_leisure and len(candidates) < 2:
        candidates.append("Time at leisure")

    if not candidates and _has(text, "coach transfer", "bus 150", "long distance panorama coach") and has_aurora:
        candidates.append("Coach journey and Northern Lights")
    if has_departure and not candidates:
        candidates.append("Departure arrangements")
    if has_arrival and not candidates:
        candidates.append("Arrival and accommodation")
    if has_hotel_only:
        candidates.append("Accommodation as listed")
    if travel_only_with_hotel and not candidates:
        if has_flight:
            candidates.append("Onward flight and accommodation")
        else:
            candidates.append("Onward travel and accommodation")
    if not candidates:
        candidates.append("Time to explore at your own pace")

    # Prefer the most distinctive compact phrase, then add at most one short
    # secondary theme if the phrase remains safely one-line in the summary table.
    primary = candidates[0]
    if len(candidates) > 1:
        combined = f"{primary}, {candidates[1].lower()}"
        if len(combined) <= 48 and not any(word in primary.lower() for word in candidates[1].lower().split()[:2]):
            return _compact_arc_phrase([combined, primary])
    return _compact_arc_phrase([primary])

def format_day_range(days):
    if not days:
        return ""

    day_numbers = [get_day_number(day) for day in days]
    day_numbers = [number for number in day_numbers if number > 0]

    if not day_numbers:
        return "TBA"

    first_day = min(day_numbers)
    last_day = max(day_numbers)

    if first_day == last_day:
        return str(first_day)

    return f"{first_day} - {last_day}"


def create_journey_arc(grouped_days):
    chapters = []

    current_city = None
    current_days = []
    current_rows = []

    for day, rows in grouped_days.items():
        city = get_primary_city(rows)

        if not city:
            city = "Cruise" if any(get_row_type(row) == "Cruise" for row in rows) else "Journey"

        if current_city is None:
            current_city = city
            current_days = [day]
            current_rows = list(rows)

        elif city == current_city:
            current_days.append(day)
            current_rows.extend(rows)

        else:
            chapters.append({
                "chapter": current_city,
                "days": format_day_range(current_days),
                "experience": describe_city_experience(current_rows),
            })

            current_city = city
            current_days = [day]
            current_rows = list(rows)

    if current_city is not None:
        chapters.append({
            "chapter": current_city,
            "days": format_day_range(current_days),
            "experience": describe_city_experience(current_rows),
        })

    return chapters
