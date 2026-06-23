"""Season-aware image matching policy for Nordic destination visuals.

This module holds visual-season and destination-profile rules that should not
be mixed into the basic metadata parser.  It protects southern/coastal city
pages from receiving snowy winter images during September/October shoulder-
season trips, while also giving each registry image profile a consistent visual
preference without hardcoding every destination in the matcher.
"""

from __future__ import annotations

from itinerary_generation.destination_registry import is_southern_coastal_destination

from .metadata import ImageCandidate, city_variants, normalize_keyword

WINTER_VISUAL_TOKENS = {
    "aurora",
    "christmas",
    "frozen",
    "ice",
    "icy",
    "northernlights",
    "snow",
    "snowy",
    "winter",
}

EXPLICIT_WINTER_INTENT_TOKENS = {
    "aurora",
    "christmas",
    "dogsledding",
    "frozen",
    "icehotel",
    "northernlights",
    "snowmobile",
    "snowshoe",
    "winter",
}

SHOULDER_SEASON_MONTHS = {9, 10}
WINTER_IMAGE_MONTHS = {11, 12, 1, 2, 3}


PROFILE_VISUAL_PREFERENCES: dict[str, tuple[str, ...]] = {
    "southern_coastal": ("coastal", "harbour", "harbor", "waterfront", "ocean", "city", "green", "summer"),
    "cruise_port": ("harbour", "harbor", "port", "waterfront", "ship", "cruise", "ocean", "coastal"),
    "island_coastal": ("island", "coastal", "ocean", "beach", "harbour", "harbor", "village"),
    "fjord": ("fjord", "mountain", "waterfall", "scenic", "cruise", "village"),
    "village": ("village", "harbour", "harbor", "mountain", "coastal", "scenic"),
    "town": ("town", "city", "street", "harbour", "harbor", "waterfront"),
    "city": ("city", "street", "architecture", "skyline", "waterfront", "oldtown"),
    "rail_hub": ("train", "rail", "railway", "station", "city", "route"),
    "mountain_resort": ("mountain", "ski", "snow", "hiking", "resort", "forest"),
    "national_park": ("national", "park", "nature", "mountain", "trail", "waterfall", "forest"),
    "arctic": ("arctic", "snow", "aurora", "winter", "fjord", "mountain", "northernlights"),
    "iceland_destination": ("lava", "waterfall", "glacier", "coastal", "village", "mountain", "black", "sand"),
    "iceland_national_park": ("national", "park", "glacier", "waterfall", "lava", "canyon", "trail"),
    "iceland_highland": ("highland", "mountain", "lava", "hiking", "scenic", "remote"),
    "iceland_route": ("route", "road", "waterfall", "coastal", "lava", "mountain"),
    "route": ("route", "road", "rail", "train", "scenic", "journey"),
    "region": ("scenic", "coastal", "mountain", "fjord", "nature"),
}

PROFILE_THEME_PREFERENCES: dict[str, tuple[str, ...]] = {
    "southern_coastal": ("waterfront", "city", "ocean", "fjord"),
    "cruise_port": ("waterfront", "ocean", "city"),
    "island_coastal": ("waterfront", "ocean", "mountain"),
    "fjord": ("fjord", "mountain", "waterfront"),
    "village": ("waterfront", "mountain", "city"),
    "town": ("city", "waterfront", "old town"),
    "city": ("city", "old town", "waterfront"),
    "rail_hub": ("train", "city", "road journey"),
    "mountain_resort": ("mountain", "winter"),
    "national_park": ("mountain", "glacier", "fjord"),
    "arctic": ("winter", "northern lights", "mountain", "fjord"),
    "iceland_destination": ("glacier", "black sand", "mountain", "waterfront"),
    "iceland_national_park": ("glacier", "mountain", "black sand"),
    "iceland_highland": ("mountain", "glacier"),
    "iceland_route": ("road journey", "mountain", "waterfront"),
    "route": ("road journey", "train", "mountain"),
    "region": ("mountain", "fjord", "waterfront"),
}


def _normalized_city_variants(value: str) -> set[str]:
    return {normalize_keyword(item) for item in city_variants(value) if normalize_keyword(item)}


def is_southern_coastal_city_context(day_context: dict) -> bool:
    variants = {str(item) for item in day_context.get("city_variants", set()) if str(item).strip()}
    city = str(day_context.get("city", "") or "").strip()
    if city:
        variants.update(_normalized_city_variants(city))
        variants.add(city)
    return any(is_southern_coastal_destination(item) for item in variants)


def _candidate_has_winter_visual(candidate: ImageCandidate) -> bool:
    tokens = set(candidate.tokens)
    themes = set(candidate.themes)
    seasons = set(candidate.seasons)
    filename = normalize_keyword(candidate.filename)
    return bool(
        tokens & WINTER_VISUAL_TOKENS
        or themes & {"winter", "northern lights", "santa", "wildlife"}
        or "winter" in seasons
        or any(token in filename.split() for token in WINTER_VISUAL_TOKENS)
    )


def _day_has_explicit_winter_intent(day_context: dict) -> bool:
    day_tokens = set(day_context.get("tokens", set()))
    day_themes = set(day_context.get("themes", set()))
    return bool(day_tokens & EXPLICIT_WINTER_INTENT_TOKENS or day_themes & {"winter", "northern lights", "santa"})


def should_block_southern_coastal_winter_image(candidate: ImageCandidate, day_context: dict) -> bool:
    """Return True when a snowy image conflicts with a southern Sep/Oct city trip."""

    month = day_context.get("month")
    try:
        month = int(month)
    except Exception:
        month = 0
    if month not in SHOULDER_SEASON_MONTHS:
        return False
    if not is_southern_coastal_city_context(day_context):
        return False
    if _day_has_explicit_winter_intent(day_context):
        return False
    return _candidate_has_winter_visual(candidate)


def shoulder_season_image_bonus(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    """Reward summer/green/coastal visuals for southern Sep/Oct city trips."""

    month = day_context.get("month")
    try:
        month = int(month)
    except Exception:
        month = 0
    if month not in SHOULDER_SEASON_MONTHS or not is_southern_coastal_city_context(day_context):
        return 0, []
    if _day_has_explicit_winter_intent(day_context):
        return 0, []

    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    candidate_seasons = set(candidate.seasons)
    score = 0
    reasons: list[str] = []

    if "summer" in candidate_seasons:
        score += 16
        reasons.append("southern coastal shoulder-season summer visual")
    if candidate_themes & {"waterfront", "city", "fjord", "mountain", "ocean"}:
        score += 8
        reasons.append("southern coastal shoulder-season visual fit")
    if candidate_tokens & {"green", "harbour", "harbor", "waterfront", "coastal", "summer", "fjord", "city"}:
        score += 6
        reasons.append("southern coastal shoulder-season keyword fit")

    return score, reasons


def destination_profile_image_bonus(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    """Reward images that match the registry image profile for the destination.

    This is deliberately a bonus, not a hard filter.  Destination folder/city
    matching still owns correctness; profile matching makes a Bergen image lean
    waterfront/coastal, a mountain resort lean mountain/ski, and an Iceland
    route lean lava/waterfall/scenic when several valid images exist.
    """

    profiles = {str(item) for item in day_context.get("image_profiles", set()) if str(item).strip()}
    if not profiles:
        return 0, []

    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    candidate_seasons = set(candidate.seasons)
    month = day_context.get("month")
    try:
        month = int(month)
    except Exception:
        month = 0

    score = 0
    reasons: list[str] = []
    for profile in sorted(profiles):
        token_matches = candidate_tokens & set(PROFILE_VISUAL_PREFERENCES.get(profile, ()))
        theme_matches = candidate_themes & set(PROFILE_THEME_PREFERENCES.get(profile, ()))
        if token_matches:
            score += min(14, 4 * len(token_matches))
            reasons.append(f"destination image profile token fit: {profile}")
        if theme_matches:
            score += min(18, 6 * len(theme_matches))
            reasons.append(f"destination image profile theme fit: {profile}")

        if profile in {"arctic", "mountain_resort"} and month in WINTER_IMAGE_MONTHS:
            if candidate_seasons & {"winter"} or candidate_tokens & {"snow", "ski", "aurora", "winter", "northernlights"}:
                score += 10
                reasons.append(f"winter visual fit for {profile}")
        elif profile in {"southern_coastal", "cruise_port", "island_coastal"} and month and month not in WINTER_IMAGE_MONTHS:
            if candidate_tokens & {"snow", "winter", "frozen", "christmas"} or "winter" in candidate_seasons:
                score -= 12
                reasons.append(f"non-winter coastal profile downranks winter visual: {profile}")

    return score, reasons
