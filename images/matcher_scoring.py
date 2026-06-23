"""Image candidate scoring helpers."""

from __future__ import annotations

from .fallback import is_global_default_candidate, score_default_candidate, _conflict_penalty
from .metadata import ImageCandidate, SEASON_ALIASES, city_variants, normalize_keyword
from .seasonal_policy import (
    destination_profile_image_bonus,
    should_block_southern_coastal_winter_image,
    shoulder_season_image_bonus,
)

DESTINATION_FOLDER_MATCH_SCORE = 60
DESTINATION_FILENAME_MATCH_SCORE = 20
SEASON_MATCH_SCORE = 24
THEME_MATCH_SCORE = 12
KEYWORD_MATCH_SCORE_PER_TOKEN = 4
KEYWORD_MATCH_SCORE_CAP = 20
COUNTRY_REGION_MATCH_SCORE = 8
SERVICE_INTENT_MATCH_SCORE = 28
SERVICE_GENERIC_CITY_PENALTY = 18




SERVICE_INTENT_MATCHERS = {
    "rail": {"themes": {"train"}, "tokens": {"train", "rail", "railway", "station", "flam", "flåm", "myrdal", "nutshell"}},
    "scenic_rail_fjord": {"themes": {"train", "fjord", "mountain"}, "tokens": {"nutshell", "flam", "flåm", "myrdal", "voss", "gudvangen", "naeroyfjord", "nærøyfjord", "fjord", "rail"}},
    "fjord_cruise": {"themes": {"fjord", "ocean", "mountain"}, "tokens": {"fjord", "cruise", "boat", "lysefjord", "preikestolen", "gudvangen", "flam", "flåm", "naeroyfjord", "nærøyfjord"}},
    "coastal_cruise": {"themes": {"fjord", "ocean", "waterfront"}, "tokens": {"coastal", "cruise", "boat", "ferry", "harbour", "harbor", "port", "sea", "fjord"}},
    "kayaking": {"themes": {"fjord", "ocean", "mountain"}, "tokens": {"kayak", "kayaking", "river", "otra", "paddle", "water"}},
    "city_walk": {"themes": {"city", "old town", "waterfront"}, "tokens": {"walking", "walk", "historic", "old", "town", "street", "streets", "bryggen"}},
    "funicular": {"themes": {"funicular", "mountain", "city"}, "tokens": {"funicular", "floibanen", "fløibanen", "floyen", "fløyen", "viewpoint", "mountain"}},
}


def _service_intent_score(candidate_tokens: set[str], candidate_themes: set[str], day_context: dict) -> tuple[int, list[str]]:
    intents = set(day_context.get("service_intents", set()) or set())
    if not intents:
        return 0, []
    score = 0
    reasons: list[str] = []
    matched_intents: list[str] = []
    for intent in sorted(intents):
        matcher = SERVICE_INTENT_MATCHERS.get(intent)
        if not matcher:
            continue
        if candidate_themes & matcher["themes"] or candidate_tokens & matcher["tokens"]:
            matched_intents.append(intent.replace("_", " "))
    if matched_intents:
        score += SERVICE_INTENT_MATCH_SCORE * min(2, len(matched_intents))
        reasons.append("service intent match: " + ", ".join(matched_intents[:3]))
        return score, reasons

    # If a day is clearly led by a scenic/transport service, a generic city
    # skyline should not win merely because the folder matches the city.
    service_led = intents & {"rail", "scenic_rail_fjord", "fjord_cruise", "coastal_cruise", "kayaking", "funicular"}
    generic_city = candidate_themes <= {"city", "waterfront", "old town"} or bool(candidate_themes & {"city"})
    if service_led and generic_city:
        return -SERVICE_GENERIC_CITY_PENALTY, ["generic city image downranked for service-led day"]
    return 0, []


def candidate_destination_matches(candidate: ImageCandidate, day_context: dict) -> bool:
    day_city_variants = set(day_context.get("city_variants", set()))
    if not day_city_variants:
        return False
    candidate_city_variants = city_variants(candidate.city)
    return bool(candidate_city_variants & day_city_variants)



def is_protected_specialty_image_allowed(candidate: ImageCandidate, day_context: dict) -> tuple[bool, str]:
    """Reject narrow specialty images unless the itinerary day explicitly asks for them.

    A picture of a polar icebreaker is visually very specific. It should not be
    used as a generic Rovaniemi/winter fallback for an accommodation day; it is
    appropriate only when the day text actually mentions a polar icebreaker or
    icebreaker cruise.
    """

    candidate_tokens = set(candidate.tokens)
    day_tokens = set(day_context.get("tokens", set()))
    day_text = str(day_context.get("text", "") or "")

    icebreaker_tokens = {"icebreaker", "icebreakercruise", "polaricebreaker"}
    if candidate_tokens & icebreaker_tokens:
        day_mentions_icebreaker = bool(day_tokens & icebreaker_tokens) or "ice breaker" in day_text
        if not day_mentions_icebreaker:
            return False, "protected specialty image requires polar icebreaker activity"

    return True, ""

def score_image_for_day(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    allowed, blocked_reason = is_protected_specialty_image_allowed(candidate, day_context)
    if not allowed:
        return 0, [blocked_reason]
    if should_block_southern_coastal_winter_image(candidate, day_context):
        return 0, ["southern coastal Sep/Oct context blocks winter image"]

    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    day_tokens = set(day_context.get("tokens", set()))
    day_season_token = normalize_keyword(day_context.get("season", ""))
    if day_season_token:
        day_tokens.add(day_season_token)
    day_themes = set(day_context.get("themes", set()))
    day_city_variants = set(day_context.get("city_variants", set()))

    candidate_city_variants = city_variants(candidate.city)
    filename_city_variants = city_variants(candidate.filename)
    day_country_variants = set(day_context.get("country_variants", set()))
    candidate_country = normalize_keyword(candidate.country)

    if is_global_default_candidate(candidate):
        return score_default_candidate(candidate, day_context)

    if not day_city_variants or not (candidate_city_variants & day_city_variants):
        return 0, ["no destination match"]

    score += DESTINATION_FOLDER_MATCH_SCORE
    reasons.append("city folder match")

    if candidate_country and candidate_country in day_country_variants:
        score += COUNTRY_REGION_MATCH_SCORE
        reasons.append(f"country/region match: {candidate_country}")

    if filename_city_variants & day_city_variants:
        score += DESTINATION_FILENAME_MATCH_SCORE
        reasons.append("city filename match")

    theme_matches = candidate_themes & day_themes
    if theme_matches:
        score += THEME_MATCH_SCORE * len(theme_matches)
        reasons.append("theme match: " + ", ".join(sorted(theme_matches)))

    service_score, service_reasons = _service_intent_score(candidate_tokens, candidate_themes, day_context)
    if service_score:
        score += service_score
        reasons.extend(service_reasons)

    day_season = normalize_keyword(day_context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if day_season and day_season in candidate_seasons:
        score += SEASON_MATCH_SCORE
        reasons.append(f"season match: {day_season}")

    token_matches = (candidate_tokens & day_tokens) - day_city_variants - set(SEASON_ALIASES)
    if token_matches:
        score += min(KEYWORD_MATCH_SCORE_CAP, KEYWORD_MATCH_SCORE_PER_TOKEN * len(token_matches))
        reasons.append("keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

    shoulder_bonus, shoulder_reasons = shoulder_season_image_bonus(candidate, day_context)
    if shoulder_bonus:
        score += shoulder_bonus
        reasons.extend(shoulder_reasons)

    profile_bonus, profile_reasons = destination_profile_image_bonus(candidate, day_context)
    if profile_bonus:
        score += profile_bonus
    if profile_reasons:
        reasons.extend(profile_reasons)

    penalty, penalty_reasons = _conflict_penalty(candidate_themes, day_themes, day_tokens)
    if penalty:
        score -= penalty
        reasons.extend(penalty_reasons)

    return score, reasons


def season_available_for_context(candidates: list[ImageCandidate], context: dict) -> bool:
    day_season = normalize_keyword(context.get("season", ""))
    if not day_season:
        return False

    for candidate in candidates:
        if should_block_southern_coastal_winter_image(candidate, context):
            continue
        if day_season not in set(candidate.seasons):
            continue
        if candidate_destination_matches(candidate, context) or is_global_default_candidate(candidate):
            return True
    return False


def _score_breakdown_from_reasons(score: int, reasons: list[str], *, is_default: bool) -> dict:
    """Return a stable explainability breakdown for selected image matches."""

    breakdown = {
        "destination_score": 0,
        "activity_product_score": 0,
        "season_score": 0,
        "country_region_score": 0,
        "fallback_score": 0,
        "total_score": score,
    }
    if is_default:
        breakdown["fallback_score"] = score
        for reason in reasons or []:
            if "fallback season match" in reason:
                breakdown["season_score"] = max(breakdown["season_score"], 8)
            if "fallback primary theme match" in reason or "fallback theme match" in reason or "fallback keyword match" in reason or "fallback context match" in reason:
                breakdown["activity_product_score"] = max(breakdown["activity_product_score"], min(score, 40))
        return breakdown

    for reason in reasons or []:
        if reason == "city folder match":
            breakdown["destination_score"] += DESTINATION_FOLDER_MATCH_SCORE
        elif reason == "city filename match":
            breakdown["destination_score"] += DESTINATION_FILENAME_MATCH_SCORE
        elif reason.startswith("country/region match"):
            breakdown["country_region_score"] += COUNTRY_REGION_MATCH_SCORE
        elif reason.startswith("season match"):
            breakdown["season_score"] += SEASON_MATCH_SCORE
        elif reason.startswith("theme match"):
            matched = [part for part in reason.split(":", 1)[-1].split(",") if part.strip()]
            breakdown["activity_product_score"] += THEME_MATCH_SCORE * max(1, len(matched))
        elif reason.startswith("keyword match"):
            matched = [part for part in reason.split(":", 1)[-1].split(",") if part.strip()]
            breakdown["activity_product_score"] += min(KEYWORD_MATCH_SCORE_CAP, KEYWORD_MATCH_SCORE_PER_TOKEN * max(1, len(matched)))
        elif reason.startswith("service intent match"):
            matched = [part for part in reason.split(":", 1)[-1].split(",") if part.strip()]
            breakdown["activity_product_score"] += SERVICE_INTENT_MATCH_SCORE * max(1, min(2, len(matched)))
        elif reason.startswith("generic city image downranked"):
            breakdown["activity_product_score"] -= SERVICE_GENERIC_CITY_PENALTY
    return breakdown


def candidate_to_payload(day: str, candidate: ImageCandidate, score: int, reasons: list[str]) -> dict:
    is_default = is_global_default_candidate(candidate)
    reason_text = "; ".join(reasons) if reasons else "destination match"
    return {
        "day": day,
        "path": candidate.path,
        "score": score,
        "reason": reason_text,
        "city": candidate.city,
        "country": candidate.country,
        "filename": candidate.filename,
        "themes": list(candidate.themes),
        "seasons": list(candidate.seasons),
        "is_default": is_default,
        "is_generic": is_default,
        "fallback_reason": reason_text if is_default else "",
        "score_breakdown": _score_breakdown_from_reasons(score, reasons, is_default=is_default),
    }


