"""Season-aware image matching policy for Nordic destination visuals.

This module holds narrow visual-season rules that should not be mixed into the
basic metadata parser.  It protects southern/coastal city pages from receiving
snowy winter images during September/October shoulder-season trips, while still
leaving Arctic/Northern destinations free to use winter imagery when it fits.
"""

from __future__ import annotations

from .metadata import ImageCandidate, city_variants, normalize_keyword

SOUTHERN_COASTAL_CITY_ALIASES = {
    "bergen",
    "kristiansand",
    "stavanger",
    "oslo",
    "copenhagen",
    "kobenhavn",
    "københavn",
    "stockholm",
    "gothenburg",
    "goteborg",
    "göteborg",
}

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


def _normalized_city_variants(value: str) -> set[str]:
    return {normalize_keyword(item) for item in city_variants(value) if normalize_keyword(item)}


def is_southern_coastal_city_context(day_context: dict) -> bool:
    variants = {normalize_keyword(item) for item in day_context.get("city_variants", set()) if normalize_keyword(item)}
    city = normalize_keyword(day_context.get("city", ""))
    if city:
        variants.update(_normalized_city_variants(city))
    return bool(variants & {normalize_keyword(item) for item in SOUTHERN_COASTAL_CITY_ALIASES})


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
