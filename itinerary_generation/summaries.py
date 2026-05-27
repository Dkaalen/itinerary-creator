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
    cities = {str(row.get("city", "")).strip().lower() for row in rows if str(row.get("city", "")).strip()}

    if has_glass_igloo_or_arctic_resort(rows):
        return "Arctic resort stay, glass igloo experience and remote Lapland scenery"

    themes = []

    if any(get_row_type(row) == "Arrival" for row in rows):
        _add_theme(themes, "arrival")

    if has_norway_in_a_nutshell(rows) or _has(text, "flåm", "flam", "nærøyfjord", "naeroyfjord", "bergen railway", "flåm railway", "flam railway"):
        _add_theme(themes, "Norway in a Nutshell route")
        _add_theme(themes, "scenic rail and fjord travel")

    if _has(text, "self-drive", "self drive", "rental vehicle", "rental suv", "route suggested", "scenic drive", "return drive", "road trip"):
        _add_theme(themes, "scenic self-drive route")

    if _has(text, "blue lagoon", "sky lagoon", "spa", "wellness", "7-step", "ritual"):
        _add_theme(themes, "lagoon and wellness experiences")

    if _has(text, "silfra", "snork"):
        _add_theme(themes, "Silfra snorkelling")

    if _has(text, "golden circle", "kerið", "kerid"):
        _add_theme(themes, "Golden Circle route")

    if _has(text, "south coast", "waterfall", "diamond beach", "black sand"):
        _add_theme(themes, "South Coast scenery")

    if _has(text, "atv", "quad", "glacier", "hike", "hiking", "crampon"):
        _add_theme(themes, "soft adventure experiences")

    if _has(text, "whale", "sea eagle", "wildlife"):
        _add_theme(themes, "coastal wildlife")

    if _has(text, "fjord", "trollfjord", "cruise", "boat", "catamaran", "silent electric ship"):
        _add_theme(themes, "fjord scenery and coastal cruising")

    if _has(text, "food", "tasting", "smørrebrød", "secret food", "fish soup", "lunch", "dinner"):
        _add_theme(themes, "local food culture")

    if _has(text, "vasa", "old town", "museum", "walking tour", "city walk", "must-see", "guided visit"):
        _add_theme(themes, "guided city discovery")

    if _has(text, "forest tower", "forgotten giants", "nature hike", "haukland", "henningsvær", "photo tour"):
        _add_theme(themes, "scenic nature experiences")

    if _has(text, "northern light", "aurora"):
        _add_theme(themes, "Northern Lights experiences")

    if _has(text, "leisure", "spend time at leisure", "free time", "explore"):
        _add_theme(themes, "time at leisure")

    if row_types == {"Hotel"}:
        _add_theme(themes, "accommodation as listed")

    if row_types.issubset({"Hotel", "Transfer"}) and any(get_row_type(row) == "Hotel" for row in rows):
        _add_theme(themes, "arrival and accommodation as listed")

    if not themes:
        if any(get_row_type(row) in {"Flight", "Train", "Transfer", "Transport"} for row in rows):
            themes.append("onward travel and accommodation as listed")
        else:
            themes.append("time to explore at your own pace")

    # Avoid generic/repeated wording when more distinctive themes exist.
    themes = [theme for theme in themes if not (theme == "guided city discovery" and len(themes) > 1 and any(t != theme for t in themes))] or themes
    return ", ".join(themes[:3]).capitalize()


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
            city = "Journey"

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
