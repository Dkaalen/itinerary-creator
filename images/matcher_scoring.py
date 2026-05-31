"""Image candidate scoring helpers."""

from __future__ import annotations

from .fallback import is_global_default_candidate, score_default_candidate, _conflict_penalty
from .metadata import ImageCandidate, SEASON_ALIASES, city_variants, normalize_keyword

DESTINATION_FOLDER_MATCH_SCORE = 60
DESTINATION_FILENAME_MATCH_SCORE = 20
SEASON_MATCH_SCORE = 24
THEME_MATCH_SCORE = 12
KEYWORD_MATCH_SCORE_PER_TOKEN = 4
KEYWORD_MATCH_SCORE_CAP = 20


def candidate_destination_matches(candidate: ImageCandidate, day_context: dict) -> bool:
    day_city_variants = set(day_context.get("city_variants", set()))
    if not day_city_variants:
        return False
    candidate_city_variants = city_variants(candidate.city)
    return bool(candidate_city_variants & day_city_variants)


def score_image_for_day(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []
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

    if is_global_default_candidate(candidate):
        return score_default_candidate(candidate, day_context)

    if not day_city_variants or not (candidate_city_variants & day_city_variants):
        return 0, ["no destination match"]

    score += DESTINATION_FOLDER_MATCH_SCORE
    reasons.append("city folder match")

    if filename_city_variants & day_city_variants:
        score += DESTINATION_FILENAME_MATCH_SCORE
        reasons.append("city filename match")

    theme_matches = candidate_themes & day_themes
    if theme_matches:
        score += THEME_MATCH_SCORE * len(theme_matches)
        reasons.append("theme match: " + ", ".join(sorted(theme_matches)))

    day_season = normalize_keyword(day_context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if day_season and day_season in candidate_seasons:
        score += SEASON_MATCH_SCORE
        reasons.append(f"season match: {day_season}")

    token_matches = (candidate_tokens & day_tokens) - day_city_variants - set(SEASON_ALIASES)
    if token_matches:
        score += min(KEYWORD_MATCH_SCORE_CAP, KEYWORD_MATCH_SCORE_PER_TOKEN * len(token_matches))
        reasons.append("keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

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
        if day_season not in set(candidate.seasons):
            continue
        if candidate_destination_matches(candidate, context) or is_global_default_candidate(candidate):
            return True
    return False


def candidate_to_payload(day: str, candidate: ImageCandidate, score: int, reasons: list[str]) -> dict:
    return {
        "day": day,
        "path": candidate.path,
        "score": score,
        "reason": "; ".join(reasons) if reasons else "destination match",
        "city": candidate.city,
        "country": candidate.country,
        "filename": candidate.filename,
        "themes": list(candidate.themes),
        "seasons": list(candidate.seasons),
    }


