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
from .scanner import get_image_bank_index


def _payload_priority_key(payload: dict | None) -> tuple:
    """Sort selected images by app priority: destination, season, activity, relevance."""

    if not payload:
        return (0, 0, 0, 0, 0, "")
    breakdown = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else {}
    is_destination = 0 if payload.get("is_default") else 1
    return (
        is_destination,
        int(breakdown.get("destination_score") or 0),
        int(breakdown.get("season_score") or 0),
        int(breakdown.get("activity_product_score") or 0),
        int(payload.get("score") or 0),
        str(payload.get("filename", "")).lower(),
    )


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
        if reusable_best is None or _payload_priority_key(payload) > _payload_priority_key(reusable_best):
            reusable_best = payload
    return reusable_best


def _attach_default_audit(
    payload: dict | None,
    context: dict,
    candidates: list[ImageCandidate],
    used_paths: set[str],
) -> dict | None:
    """Annotate default selections with proof that no stronger match was available."""

    if not payload or not payload.get("is_default"):
        return payload

    require_matching_season = season_available_for_context(candidates, context)
    day_season = normalize_keyword(context.get("season", ""))
    best_non_default: dict | None = None
    best_reused_non_default: dict | None = None

    for candidate in candidates:
        if is_global_default_candidate(candidate):
            continue
        normalized_path = str(Path(candidate.path).resolve())
        if require_matching_season and day_season not in set(candidate.seasons):
            continue
        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        candidate_payload = candidate_to_payload(str(payload.get("day", "")), candidate, score, reasons)
        if normalized_path in used_paths:
            if best_reused_non_default is None or _payload_priority_key(candidate_payload) > _payload_priority_key(best_reused_non_default):
                best_reused_non_default = candidate_payload
            continue
        if best_non_default is None or _payload_priority_key(candidate_payload) > _payload_priority_key(best_non_default):
            best_non_default = candidate_payload

    selected_score = int(payload.get("score") or 0)
    stronger_available = bool(best_non_default and int(best_non_default.get("score") or 0) > selected_score)
    payload["stronger_candidate_available"] = stronger_available
    payload["audit"] = {
        "selected_default": True,
        "stronger_candidate_available": stronger_available,
        "best_non_default_score": int(best_non_default.get("score") or 0) if best_non_default else 0,
        "best_non_default_path": str(best_non_default.get("path", "")) if best_non_default else "",
        "best_reused_non_default_score": int(best_reused_non_default.get("score") or 0) if best_reused_non_default else 0,
        "best_reused_non_default_path": str(best_reused_non_default.get("path", "")) if best_reused_non_default else "",
        "fallback_proof": (
            "stronger unused destination/activity match exists"
            if stronger_available
            else "no stronger unused destination/activity match available"
        ),
    }
    return payload


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
            if best_default is None or _payload_priority_key(payload) > _payload_priority_key(best_default):
                best_default = payload
        else:
            if best_destination is None or _payload_priority_key(payload) > _payload_priority_key(best_destination):
                best_destination = payload

    if best_destination:
        return best_destination

    best = best_default
    if best:
        if allow_default_repair:
            reusable = _best_reusable_default(day, context, candidates)
            if reusable and reusable.get("score", 0) >= best.get("score", 0) + 12:
                return _attach_default_audit(reusable, context, candidates, used_paths)
        return _attach_default_audit(best, context, candidates, used_paths)
    if not allow_default_repair:
        return best

    default_candidates = [
        candidate for candidate in candidates
        if is_global_default_candidate(candidate)
        and str(Path(candidate.path).resolve()) not in used_paths
    ]
    if not default_candidates:
        return _attach_default_audit(_best_reusable_default(day, context, candidates), context, candidates, used_paths)

    default_best = None
    for candidate in default_candidates:
        allowed, blocked_reason = is_protected_specialty_image_allowed(candidate, context)
        if not allowed:
            continue
        score, reasons = score_default_candidate(candidate, context)
        score = max(1, score)
        reasons = list(reasons or []) + ["defensive default repair"]
        payload = candidate_to_payload(day, candidate, score, reasons)
        if default_best is None or _payload_priority_key(payload) > _payload_priority_key(default_best):
            default_best = payload

    # If the only unused default is an obvious semantic conflict, reuse a
    # safer default image rather than forcing a reindeer/aurora/winter image
    # onto a summer city or culture day. This preserves uniqueness in normal
    # cases while avoiding the most visible bad matches.
    reusable = _best_reusable_default(day, context, candidates)
    if reusable and (not default_best or reusable.get("score", 0) >= default_best.get("score", 0) + 12):
        default_best = reusable
    return _attach_default_audit(default_best, context, candidates, used_paths)


def select_day_image(day: str, rows: list[dict], image_bank_path: Path | str = "image_bank") -> dict | None:
    index = get_image_bank_index(image_bank_path)
    if not index.candidates:
        return None
    context = build_day_context(day, rows)
    candidates = list(index.candidates_for_context(context))
    return select_best_candidate_for_context(day, context, candidates)


def select_day_images(
    grouped_days: dict,
    image_bank_path: Path | str = "image_bank",
    used_paths: set[str] | None = None,
) -> dict:
    """Select at most one non-reused image for each day in itinerary order."""
    index = get_image_bank_index(image_bank_path)
    if not index.candidates:
        return {day: None for day in (grouped_days or {})}

    matches = {}
    used_paths = {str(Path(path).resolve()) for path in (used_paths or set())}
    for day, rows in (grouped_days or {}).items():
        context = build_day_context(day, rows)
        candidates = list(index.candidates_for_context(context))
        match = select_best_candidate_for_context(day, context, candidates, used_paths)
        matches[day] = match
        if match:
            used_paths.add(str(Path(match["path"]).resolve()))
    return matches


