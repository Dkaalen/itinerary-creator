"""Image selection helpers for itinerary days."""

from __future__ import annotations

from pathlib import Path

from .fallback import is_global_default_candidate, score_default_candidate
from .metadata import ImageCandidate, normalize_keyword
from .matcher_context import build_day_context
from .matcher_scoring import (
    candidate_to_payload,
    score_image_for_day,
    season_available_for_context,
)
from .scanner import scan_image_bank


def select_best_candidate_for_context(
    day: str,
    context: dict,
    candidates: list[ImageCandidate],
    used_paths: set[str] | None = None,
    *,
    allow_default_repair: bool = True,
) -> dict | None:
    used_paths = used_paths or set()
    best = None
    require_matching_season = season_available_for_context(candidates, context)
    day_season = normalize_keyword(context.get("season", ""))

    for candidate in candidates:
        normalized_path = str(Path(candidate.path).resolve())
        if normalized_path in used_paths:
            continue
        if require_matching_season and day_season not in set(candidate.seasons):
            # Destination-specific images should stay season-aware when possible.
            # Default fallback images are different: if the Default bank has no
            # winter city/road/train image, a semantically relevant non-seasonal
            # image is better than a random winter image. Let Default candidates
            # compete by score instead of hard-filtering them by season.
            if not is_global_default_candidate(candidate):
                continue

        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        payload = candidate_to_payload(day, candidate, score, reasons)
        if best is None or (payload["score"], payload["filename"]) > (best["score"], best["filename"]):
            best = payload

    if best or not allow_default_repair:
        return best

    default_candidates = [
        candidate for candidate in candidates
        if is_global_default_candidate(candidate)
        and str(Path(candidate.path).resolve()) not in used_paths
    ]
    if not default_candidates:
        return None

    default_best = None
    for candidate in default_candidates:
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
    if default_best and default_best.get("score", 0) <= 5:
        for candidate in [c for c in candidates if is_global_default_candidate(c)]:
            score, reasons = score_default_candidate(candidate, context)
            if score <= default_best.get("score", 0):
                continue
            payload = candidate_to_payload(day, candidate, score, list(reasons or []) + ["safe default reuse to avoid conflict"])
            if default_best is None or (payload["score"], payload["filename"]) > (default_best["score"], default_best["filename"]):
                default_best = payload
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


