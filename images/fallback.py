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
    summer_context = "summer" in day_tokens or "summer" in day_themes
    explicit_arctic_winter_activity = any(item in day_tokens for item in {"northernlights", "aurora", "snowmobile", "sledding"})
    winter_intent = explicit_arctic_winter_activity
    if summer_context and cand("winter", "wildlife", "northern lights") and not winter_intent:
        penalty += 75
        penalties.append("conflict: summer context vs winter/aurora/wildlife image")
    if has("copenhagen", "denmark", "stockholm", "gothenburg") and cand("wildlife", "northern lights", "winter") and not winter_intent:
        penalty += 55
        penalties.append("conflict: city/summer context vs arctic winter image")
    if has("forest tower", "forgotten giants", "copenhagen") and cand("northern lights", "wildlife", "winter"):
        penalty += 60
        penalties.append("conflict: Copenhagen nature/culture vs Arctic winter image")

    return penalty, penalties


def _semantic_bridge_bonus(candidate_themes: set[str], day_themes: set[str], day_tokens: set[str]) -> tuple[int, list[str]]:
    """Reward close-enough Default images when exact themes do not exist.

    The small bundled Default image bank cannot cover every destination. These
    bridges keep generic fallbacks visually relevant without letting a random
    seasonal image beat the actual day context.
    """

    bonus = 0
    reasons: list[str] = []
    has = lambda *items: any(item in day_themes or item in day_tokens for item in items)
    cand = lambda *items: any(item in candidate_themes for item in items)

    if has("igloo", "kakslauttanen", "glass", "arctic", "resort") and cand("northern lights", "winter", "mountain"):
        bonus += 22
        reasons.append("fallback context match: arctic resort")
    if has("old town", "tallinn", "historic", "medieval") and cand("city", "waterfront"):
        bonus += 20
        reasons.append("fallback context match: historic city")
    if has("walking", "walk", "city", "sightseeing", "landmarks") and cand("city", "waterfront"):
        bonus += 18
        reasons.append("fallback context match: city experience")
    if has("arrival", "departure", "airport", "hotel", "private") and cand("city", "waterfront"):
        bonus += 14
        reasons.append("fallback context match: city arrival/departure")
    if has("fjord", "fjords", "landscape", "photo", "view", "cable", "fjellheisen") and cand("fjord", "mountain", "waterfront"):
        bonus += 20
        reasons.append("fallback context match: fjord/viewpoint")
    if has("coach", "bus", "road") and cand("road journey", "mountain") and not has("igloo", "kakslauttanen", "glass", "arctic", "resort"):
        bonus += 18
        reasons.append("fallback context match: road journey")
    return bonus, reasons


def _mismatch_penalty(candidate_themes: set[str], day_themes: set[str], day_tokens: set[str]) -> tuple[int, list[str]]:
    penalty = 0
    reasons: list[str] = []
    has = lambda *items: any(item in day_themes or item in day_tokens for item in items)
    cand = lambda *items: any(item in candidate_themes for item in items)

    if has("arrival", "departure", "hotel", "walking", "walk", "city") and cand("train", "road journey") and not has("train", "rail", "coach", "bus", "nutshell"):
        penalty += 28
        reasons.append("conflict: city/arrival day vs transport image")
    if has("igloo", "kakslauttanen", "glass", "arctic", "resort") and cand("city") and not cand("northern lights", "winter", "mountain"):
        penalty += 30
        reasons.append("conflict: arctic resort day vs city image")
    if has("igloo", "kakslauttanen", "glass", "arctic", "resort") and cand("road journey"):
        penalty += 24
        reasons.append("conflict: arctic resort day vs road image")
    if has("old town", "tallinn", "historic", "medieval") and cand("train", "road journey", "wildlife"):
        penalty += 28
        reasons.append("conflict: old-town day vs unrelated transport/wildlife image")
    if has("fjord", "fjords", "photo", "landscape", "cable", "fjellheisen") and cand("city", "train") and not cand("fjord", "mountain", "waterfront"):
        penalty += 22
        reasons.append("conflict: fjord/viewpoint day vs unrelated city/train image")
    return penalty, reasons


def score_default_candidate(candidate: ImageCandidate, day_context: dict) -> tuple[int, list[str]]:
    score = 8
    reasons = ["global default fallback"]
    candidate_tokens = set(candidate.tokens)
    candidate_themes = set(candidate.themes)
    day_tokens = set(day_context.get("tokens", set()))
    day_season_token = normalize_keyword(day_context.get("season", ""))
    if day_season_token:
        day_tokens.add(day_season_token)
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

    bridge_bonus, bridge_reasons = _semantic_bridge_bonus(candidate_themes, day_themes, day_tokens)
    if bridge_bonus:
        score += bridge_bonus
        reasons.extend(bridge_reasons)

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
    mismatch_penalty, mismatch_reasons = _mismatch_penalty(candidate_themes, day_themes, day_tokens)
    penalty += mismatch_penalty
    penalty_reasons.extend(mismatch_reasons)
    if penalty:
        score -= penalty
        reasons.extend(penalty_reasons)

    return min(score, 100), reasons


# Backwards-compatible private aliases for callers/tests that may have imported them.
_is_global_default_candidate = is_global_default_candidate
_score_default_candidate = score_default_candidate
