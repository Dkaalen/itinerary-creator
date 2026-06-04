"""Image selection helpers for itinerary days."""

from __future__ import annotations

from pathlib import Path

from .fallback import is_global_default_candidate, score_default_candidate
from .metadata import ImageCandidate, normalize_keyword
from .matcher_context import build_day_context
from .matcher_scoring import (
    candidate_to_payload,
    is_protected_specialty_image_allowed,
    score_image_for_day,
    season_available_for_context,
)
from .scanner import scan_image_bank


def _best_reusable_default(day: str, context: dict, candidates: list[ImageCandidate], minimum_score: int = 38) -> dict | None:
    reusable_best = None
    for candidate in candidates:
        if not is_global_default_candidate(candidate):
            continue
        allowed, blocked_reason = is_protected_specialty_image_allowed(candidate, context)
        if not allowed:
            continue
        score, reasons = score_default_candidate(candidate, context)
        if score < minimum_score:
            continue
        payload = candidate_to_payload(day, candidate, score, list(reasons or []) + ["reused strong default to avoid weak fallback"])
        if reusable_best is None or (payload["score"], payload["filename"]) > (reusable_best["score"], reusable_best["filename"]):
            reusable_best = payload
    return reusable_best


def select_best_candidate_for_context(
    day: str,
    context: dict,
    candidates: list[ImageCandidate],
    used_paths: set[str] | None = None,
    *,
    allow_default_repair: bool = True,
) -> dict | None:
    used_paths = used_paths or set()
    best_destination = None
    best_default = None
    require_matching_season = season_available_for_context(candidates, context)
    day_season = normalize_keyword(context.get("season", ""))

    for candidate in candidates:
        normalized_path = str(Path(candidate.path).resolve())
        if normalized_path in used_paths:
            continue
        is_default = is_global_default_candidate(candidate)
        if require_matching_season and day_season not in set(candidate.seasons):
            # Destination-specific images should stay season-aware when possible.
            # Default fallback images are different: if the Default bank has no
            # matching-season city/road/train image, a semantically relevant
            # non-seasonal image is better than a random seasonal image.
            if not is_default:
                continue

        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        payload = candidate_to_payload(day, candidate, score, reasons)
        if is_default:
            if best_default is None or (payload["score"], payload["filename"]) > (best_default["score"], best_default["filename"]):
                best_default = payload
        else:
            if best_destination is None or (payload["score"], payload["filename"]) > (best_destination["score"], best_destination["filename"]):
                best_destination = payload

    if best_destination:
        return best_destination

    best = best_default
    if best:
        if allow_default_repair:
            reusable = _best_reusable_default(day, context, candidates)
            if reusable and reusable.get("score", 0) >= best.get("score", 0) + 12:
                return reusable
        return best
    if not allow_default_repair:
        return best

    default_candidates = [
        candidate for candidate in candidates
        if is_global_default_candidate(candidate)
        and str(Path(candidate.path).resolve()) not in used_paths
    ]
    if not default_candidates:
        return _best_reusable_default(day, context, candidates)

    default_best = None
    for candidate in default_candidates:
        allowed, blocked_reason = is_protected_specialty_image_allowed(candidate, context)
        if not allowed:
            continue
        score, reasons = score_default_candidate(candidate, context)
        score = max(1, score)
        reasons = list(reasons or []) + ["defensive default repair"]
        payload = candidate_to_payload(day, candidate, score, reasons)
        if default_best is None or (payload["score"], payload["filename"]) > (default_best["score"], default_best["filename"]):
            default_best = payload

    # If the only unused default is an obvious semantic conflict, reuse a
    # safer default image rather than forcing a reindeer/aurora/winter image
    # onto a summer city or culture day. This preserves uniqueness in normal
    # cases while avoiding the most visible bad matches.
    reusable = _best_reusable_default(day, context, candidates)
    if reusable and (not default_best or reusable.get("score", 0) >= default_best.get("score", 0) + 12):
        default_best = reusable
    return default_best


def select_day_image(day: str, rows: list[dict], image_bank_path: Path | str = "image_bank") -> dict | None:
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return None
    context = build_day_context(day, rows)
    return select_best_candidate_for_context(day, context, candidates)


def select_day_images(
    grouped_days: dict,
    image_bank_path: Path | str = "image_bank",
    used_paths: set[str] | None = None,
) -> dict:
    """Select at most one non-reused image for each day in itinerary order."""
    candidates = scan_image_bank(image_bank_path)
    if not candidates:
        return {day: None for day in (grouped_days or {})}

    matches = {}
    used_paths = {str(Path(path).resolve()) for path in (used_paths or set())}
    for day, rows in (grouped_days or {}).items():
        context = build_day_context(day, rows)
        match = select_best_candidate_for_context(day, context, candidates, used_paths)
        matches[day] = match
        if match:
            used_paths.add(str(Path(match["path"]).resolve()))
    return matches


