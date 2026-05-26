"""Global Default image fallback scoring."""

from __future__ import annotations

from .metadata import ImageCandidate, normalize_keyword


def is_global_default_candidate(candidate: ImageCandidate) -> bool:
    return normalize_keyword(candidate.city) in {"default", "defoult"}


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

    return min(score, 55), reasons


# Backwards-compatible private aliases for callers/tests that may have imported them.
_is_global_default_candidate = is_global_default_candidate
_score_default_candidate = score_default_candidate
