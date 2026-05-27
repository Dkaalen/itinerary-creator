"""Global Default image fallback scoring."""

from __future__ import annotations

from .metadata import ImageCandidate, normalize_keyword


def is_global_default_candidate(candidate: ImageCandidate) -> bool:
    return normalize_keyword(candidate.city) in {"default", "defoult"}


def _conflict_penalty(candidate_themes: set[str], day_themes: set[str], day_tokens: set[str]) -> tuple[int, list[str]]:
    """Penalize obviously contradictory default images.

    This is intentionally generic: it rejects broad semantic conflicts rather
    than tailoring to any one itinerary or destination.
    """
    penalties = []
    penalty = 0

    has = lambda *items: any(item in day_themes or item in day_tokens for item in items)
    cand = lambda *items: any(item in candidate_themes for item in items)

    if has("ocean", "whale", "whales", "boat") and cand("wildlife", "winter"):
        penalty += 35
        penalties.append("conflict: ocean activity vs wildlife/winter image")
    if has("lagoon", "spa", "ritual", "wellness") and cand("city", "train", "wildlife"):
        penalty += 35
        penalties.append("conflict: lagoon/spa activity vs unrelated image")
    if has("glacier", "crampon", "crampons") and cand("city", "train", "wildlife"):
        penalty += 30
        penalties.append("conflict: glacier activity vs unrelated image")
    if has("black sand", "atv", "quad", "beach") and cand("city", "train", "wildlife"):
        penalty += 25
        penalties.append("conflict: outdoor route/activity vs unrelated image")
    if has("summer") and cand("winter", "wildlife") and not (day_themes & {"winter", "northern lights"}):
        penalty += 20
        penalties.append("conflict: summer context vs winter image")

    return penalty, penalties


def score_default_candidate(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    score = 8
    reasons = ["global default fallback"]
    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    day_tokens = set(day_context.get("tokens", set()))
    day_themes = set(day_context.get("themes", set()))
    primary_themes = set(day_context.get("primary_themes", set()))

    primary_theme_matches = candidate_themes & primary_themes
    if primary_theme_matches:
        score += 22 * len(primary_theme_matches)
        reasons.append("fallback primary theme match: " + ", ".join(sorted(primary_theme_matches)))

    theme_matches = (candidate_themes & day_themes) - primary_theme_matches
    if theme_matches:
        score += 20 * len(theme_matches)
        reasons.append("fallback theme match: " + ", ".join(sorted(theme_matches)))

    day_season = normalize_keyword(day_context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if day_season and day_season in candidate_seasons:
        score += 8
        reasons.append(f"fallback season match: {day_season}")

    token_matches = (candidate_tokens & day_tokens) - {"default", "summer", "winter", "unknown"}
    if token_matches:
        score += min(16, 3 * len(token_matches))
        reasons.append("fallback keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

    penalty, penalty_reasons = _conflict_penalty(candidate_themes, day_themes, day_tokens)
    if penalty:
        score -= penalty
        reasons.extend(penalty_reasons)

    return min(score, 55), reasons


# Backwards-compatible private aliases for callers/tests that may have imported them.
_is_global_default_candidate = is_global_default_candidate
_score_default_candidate = score_default_candidate
