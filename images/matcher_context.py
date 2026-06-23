"""Day-context construction for image matching."""

from __future__ import annotations

from itinerary_generation.destination_registry import destination_country_for_alias, destination_for_alias

from .metadata import CITY_ALIASES, city_variants, infer_primary_month_from_rows, infer_season_from_rows, infer_themes, normalize_keyword, tokenize

CITY_TO_COUNTRY = {
    "oslo": "norway",
    "bergen": "norway",
    "kristiansand": "norway",
    "stavanger": "norway",
    "tromso": "norway",
    "tromsø": "norway",
    "flam": "norway",
    "flåm": "norway",
    "alesund": "norway",
    "ålesund": "norway",
    "helsinki": "finland",
    "rovaniemi": "finland",
    "kakslauttanen": "finland",
    "kakslauttenen": "finland",
    "ivalo": "finland",
    "tallinn": "estonia",
    "stockholm": "sweden",
    "kiruna": "sweden",
    "abisko": "sweden",
    "gallivare": "sweden",
    "gällivare": "sweden",
    "copenhagen": "denmark",
    "kobenhavn": "denmark",
    "københavn": "denmark",
    "reykjavik": "iceland",
    "reykjavík": "iceland",
    "keflavik": "iceland",
    "keflavík": "iceland",
    "vik": "iceland",
    "vík": "iceland",
    "hella": "iceland",
    "hofn": "iceland",
    "höfn": "iceland",
    "akureyri": "iceland",
}


def _country_variants_for_city(city: str) -> set[str]:
    variants = set()
    for city_variant in city_variants(city):
        country = destination_country_for_alias(city_variant) or CITY_TO_COUNTRY.get(normalize_keyword(city_variant), "")
        if country:
            variants.add(country)
    return variants



def _destination_profiles_for_city(city: str) -> tuple[set[str], set[str]]:
    image_profiles: set[str] = set()
    season_profiles: set[str] = set()
    for city_variant in city_variants(city):
        record = destination_for_alias(city_variant)
        if record is None:
            continue
        if record.image_profile:
            image_profiles.add(record.image_profile)
        if record.season_profile:
            season_profiles.add(record.season_profile)
    return image_profiles, season_profiles

def _row_type(row: dict) -> str:
    return normalize_keyword(row.get("effective_type") or row.get("type") or "")


def _row_text(row: dict) -> str:
    return " ".join([
        str(row.get("city", "") or ""),
        str(row.get("title", "") or ""),
        str(row.get("original_title", "") or ""),
        str(row.get("details", "") or ""),
        str(row.get("display_description", "") or ""),
        " ".join(row.get("includes", []) or []),
    ])




SERVICE_INTENT_KEYWORDS = {
    "rail": {"train", "rail", "railway", "flam", "flåm", "myrdal", "nutshell"},
    "fjord_cruise": {"fjord", "cruise", "boat", "lysefjord", "preikestolen", "naeroyfjord", "nærøyfjord", "flam", "flåm", "gudvangen"},
    "coastal_cruise": {"coastal", "cruise", "ferry", "port", "harbour", "harbor", "fjord", "lounge"},
    "kayaking": {"kayak", "kayaking", "river", "otra", "paddle"},
    "city_walk": {"walking", "walk", "historic", "old", "town", "guide", "guided"},
    "funicular": {"funicular", "floibanen", "fløibanen", "fløyen", "floyen", "mount", "viewpoint"},
}


def _service_intents_for_rows(rows: list[dict]) -> set[str]:
    intents: set[str] = set()
    normalized_text = normalize_keyword(" ".join(_row_text(row) for row in rows or []))
    tokens = tokenize(normalized_text)
    row_types = {_row_type(row) for row in rows or []}

    if "norway in a nutshell" in normalized_text or "nutshell" in tokens:
        intents.update({"scenic_rail_fjord", "rail", "fjord_cruise"})
    if "lysefjord" in tokens or "preikestolen" in tokens:
        intents.add("fjord_cruise")
    if "coastal cruise" in normalized_text or "atlantic coastal" in normalized_text:
        intents.add("coastal_cruise")
    if row_types & {"train"} or tokens & SERVICE_INTENT_KEYWORDS["rail"]:
        intents.add("rail")
    if row_types & {"cruise", "ferry"} or tokens & {"fjord", "cruise", "boat"}:
        intents.add("fjord_cruise" if tokens & {"fjord", "lysefjord", "preikestolen", "naeroyfjord", "gudvangen", "flam", "flåm"} else "coastal_cruise")
    if tokens & SERVICE_INTENT_KEYWORDS["kayaking"]:
        intents.add("kayaking")
    if tokens & SERVICE_INTENT_KEYWORDS["funicular"]:
        intents.add("funicular")
    if tokens & SERVICE_INTENT_KEYWORDS["city_walk"]:
        intents.add("city_walk")

    # Pure arrival/departure/hotel days should remain city-led instead of
    # being pulled toward generic transport visuals.
    if row_types <= {"arrival", "departure", "hotel", "accommodation", "leisure", "transfer"} and not (tokens & {"train", "cruise", "fjord", "kayak", "funicular"}):
        intents.discard("coastal_cruise")
        intents.discard("fjord_cruise")
    return intents


def _service_destination_variants(intents: set[str], text: str) -> set[str]:
    variants: set[str] = set()
    normalized_text = normalize_keyword(text)
    if "scenic_rail_fjord" in intents or "norway in a nutshell" in normalized_text:
        for place in ("Bergen", "Voss", "Gudvangen", "Flåm", "Flam", "Myrdal", "Oslo", "Nærøyfjord", "Naeroyfjord"):
            variants.update(city_variants(place))
    if "fjord_cruise" in intents and ("lysefjord" in normalized_text or "preikestolen" in normalized_text):
        for place in ("Stavanger", "Lysefjord", "Preikestolen"):
            variants.update(city_variants(place))
    return variants


def _themes_for_rows(rows: list[dict]) -> set[str]:
    text_parts = []
    hinted = set()
    for row in rows or []:
        row_type = _row_type(row)
        row_text = _row_text(row)
        row_tokens = tokenize(row_text)
        text_parts.append(row_text)
        if row_type in {"hotel", "accommodation", "arrival", "departure"}:
            hinted.add("city")
        if row_type in {"transfer", "transport", "drive", "car"}:
            if row_tokens & {"private", "airport", "hotel", "station"}:
                hinted.add("city")
            if row_tokens & {"train", "rail", "railway", "express", "overnight"}:
                hinted.add("train")
            if row_tokens & {"coach", "bus", "road", "route", "drive", "driving", "vehicle", "car"}:
                hinted.add("road journey")
    tokens = tokenize(" ".join(text_parts))
    return infer_themes(tokens) | hinted



def _known_destination_from_text(text: str, current_city: str = "") -> str:
    """Infer a meaningful image destination mentioned in activity text.

    Some rows keep the overnight/base city in the City column even when the
    actual experience is a cross-border or day-trip destination, for example
    Helsinki rows titled "Day Trip to Tallinn". Prefer that explicit
    destination for image matching so the day image reflects the experience.
    """

    normalized_text = normalize_keyword(text)
    current_variants = city_variants(current_city)
    if not normalized_text:
        return ""

    ordered_aliases = sorted(CITY_ALIASES.items(), key=lambda item: -max(len(str(alias)) for alias in item[1]))
    for canonical, aliases in ordered_aliases:
        normalized_aliases = {normalize_keyword(alias) for alias in aliases}
        if current_variants & normalized_aliases:
            continue
        for alias in normalized_aliases:
            if not alias:
                continue
            patterns = [
                f"to {alias}",
                f"in {alias}",
                f"old town {alias}",
                f"{alias} old town",
                f"{alias} day trip",
                f"day trip to {alias}",
                f"excursion to {alias}",
            ]
            if any(pattern in normalized_text for pattern in patterns):
                return canonical.title() if canonical.isascii() else canonical
    return ""

def _select_primary_image_city(rows: list[dict]) -> str:
    """Pick the destination that should drive day-image matching.

    Do not blindly use the first city on the day. Self-drive itineraries often
    start a day with arrival/car/drive rows in the origin city while the page
    heading and main experience are in the destination city. Activity rows are
    the best first signal, followed by accommodation, then travel/departure rows.
    """

    priority_groups = [
        {"activity", "day overview"},
        {"hotel", "accommodation"},
        {"train", "flight", "cruise", "ferry", "transport", "transfer"},
        {"arrival", "departure", "leisure", "drive", "car"},
    ]
    for group in priority_groups:
        for row in rows or []:
            row_type = _row_type(row)
            city = str(row.get("city", "") or "").strip()
            if not city or row_type not in group:
                continue
            if row_type in {"activity", "day overview"}:
                text_destination = _known_destination_from_text(_row_text(row), city)
                if text_destination:
                    return text_destination
            return city
    for row in rows or []:
        city = str(row.get("city", "") or "").strip()
        if city:
            return city
    return ""


def _all_city_variants(rows: list[dict], primary_city: str) -> set[str]:
    variants = set(city_variants(primary_city))
    for row in rows or []:
        row_type = _row_type(row)
        city = str(row.get("city", "") or "").strip()
        if not city:
            continue
        # Keep activity/hotel cities as secondary matches. Avoid adding every
        # origin city from drive/car rows because that can make generic origin
        # images beat the day's actual destination.
        if row_type in {"activity", "hotel", "accommodation", "day overview"}:
            variants.update(city_variants(city))
    return variants


def build_day_context(day: str, rows: list[dict]) -> dict:
    city = _select_primary_image_city(rows or [])
    parts = [day]
    for row in rows or []:
        parts.append(_row_text(row))

    non_transport_rows = [
        row for row in (rows or [])
        if _row_type(row) not in {"transfer", "transport", "drive", "car"}
    ]
    primary_rows = non_transport_rows or list(rows or [])

    text = " ".join(parts)
    tokens = tokenize(text)
    themes = infer_themes(tokens) | _themes_for_rows(rows or [])
    primary_themes = _themes_for_rows(primary_rows)
    service_intents = _service_intents_for_rows(rows or [])
    if service_intents & {"rail", "fjord_cruise", "coastal_cruise", "scenic_rail_fjord", "kayaking", "funicular"}:
        themes.update(intent.replace("_", " ") for intent in service_intents)
    city_variant_values = _all_city_variants(rows or [], city)
    city_variant_values.update(_service_destination_variants(service_intents, text))
    country_variants = _country_variants_for_city(city)
    image_profiles, season_profiles = _destination_profiles_for_city(city)
    for row in rows or []:
        row_city = str(row.get("city", "") or "").strip()
        country_variants.update(_country_variants_for_city(row_city))
        row_image_profiles, row_season_profiles = _destination_profiles_for_city(row_city)
        image_profiles.update(row_image_profiles)
        season_profiles.update(row_season_profiles)

    return {
        "day": day,
        "city": city,
        "city_variants": city_variant_values,
        "country_variants": country_variants,
        "tokens": tokens,
        "themes": themes,
        "primary_themes": primary_themes,
        "season": infer_season_from_rows(rows),
        "month": infer_primary_month_from_rows(rows),
        "image_profiles": image_profiles,
        "season_profiles": season_profiles,
        "service_intents": service_intents,
        "text": normalize_keyword(text),
    }
