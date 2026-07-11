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


def _has_conflict(reasons: list[str] | tuple[str, ...] | None) -> bool:
    """Return whether scoring identified a semantic image/day conflict."""

    return any(str(reason).lower().startswith("conflict:") for reason in (reasons or ()))


def _safe_matching_season_available(context: dict, candidates: list[ImageCandidate]) -> bool:
    """Return whether the bank has a safe candidate for the day season."""

    day_season = normalize_keyword(context.get("season", ""))
    if not day_season:
        return False
    for candidate in candidates:
        if day_season not in set(candidate.seasons):
            continue
        allowed, _blocked_reason = is_protected_specialty_image_allowed(candidate, context)
        if not allowed:
            continue
        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        if is_global_default_candidate(candidate) and _has_conflict(reasons):
            continue
        return True
    return False


def _candidate_season_compatible(candidate: ImageCandidate, context: dict, candidates: list[ImageCandidate]) -> bool:
    """Prefer truthful seasons without forcing a semantically unsafe image."""

    day_season = normalize_keyword(context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if not day_season or not candidate_seasons or day_season in candidate_seasons:
        return True
    return not _safe_matching_season_available(context, candidates)


def _best_reusable_default(day: str, context: dict, candidates: list[ImageCandidate], minimum_score: int = 1) -> dict | None:
    """Return the strongest safe Default image, allowing intentional reuse.

    The bundled bank is deliberately small. Once its unused safe images are
    exhausted, repeating a season/context-compatible landscape is better than
    forcing a contradictory winter, wildlife or transport image onto the day.
    """

    reusable_best = None
    for candidate in candidates:
        if not is_global_default_candidate(candidate):
            continue
        if not _candidate_season_compatible(candidate, context, candidates):
            continue
        allowed, _blocked_reason = is_protected_specialty_image_allowed(candidate, context)
        if not allowed:
            continue
        score, reasons = score_default_candidate(candidate, context)
        if score < minimum_score or _has_conflict(reasons):
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

    best_non_default: dict | None = None
    best_reused_non_default: dict | None = None

    for candidate in candidates:
        if is_global_default_candidate(candidate):
            continue
        normalized_path = str(Path(candidate.path).resolve())
        if not _candidate_season_compatible(candidate, context, candidates):
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

    for candidate in candidates:
        normalized_path = str(Path(candidate.path).resolve())
        if normalized_path in used_paths:
            continue
        is_default = is_global_default_candidate(candidate)
        if not _candidate_season_compatible(candidate, context, candidates):
            # Never use an explicitly wrong-season image while a matching-season
            # candidate exists. Season-neutral images remain eligible.
            continue

        score, reasons = score_image_for_day(candidate, context)
        if score <= 0 or (is_default and _has_conflict(reasons)):
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
        if not _candidate_season_compatible(candidate, context, candidates):
            continue
        allowed, blocked_reason = is_protected_specialty_image_allowed(candidate, context)
        if not allowed:
            continue
        score, reasons = score_default_candidate(candidate, context)
        if score <= 0 or _has_conflict(reasons):
            continue
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


def _candidate_payload_for_global_assignment(
    day: str,
    context: dict,
    candidate: ImageCandidate,
    candidates: list[ImageCandidate],
    used_paths: set[str],
) -> dict | None:
    normalized_path = str(Path(candidate.path).resolve())
    if normalized_path in used_paths:
        return None
    is_default = is_global_default_candidate(candidate)
    if not _candidate_season_compatible(candidate, context, candidates):
        return None
    score, reasons = score_image_for_day(candidate, context)
    if score <= 0 or (is_default and _has_conflict(reasons)):
        return None
    payload = candidate_to_payload(day, candidate, score, list(reasons or []) + ["global itinerary image assignment"])
    return payload


def _global_assignment_priority(payload: dict) -> tuple:
    breakdown = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else {}
    return (
        int(payload.get("score") or 0),
        int(breakdown.get("activity_product_score") or 0),
        int(breakdown.get("destination_score") or 0),
        int(breakdown.get("season_score") or 0),
        str(payload.get("filename", "")).lower(),
    )


def _assign_payloads_globally(matches: dict, payloads: list[dict], used_paths: set[str]) -> None:
    for payload in sorted(payloads, key=_global_assignment_priority, reverse=True):
        day = payload.get("day")
        if day in matches and matches[day] is not None:
            continue
        path_key = str(Path(payload.get("path", "")).resolve())
        if path_key in used_paths:
            continue
        matches[day] = payload
        used_paths.add(path_key)


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
    """Select one image per day after scoring the whole itinerary.

    The old greedy pass let an earlier weak context claim an image that was a
    stronger exact match for a later day.  This pass scores every day/image
    pair first, assigns destination images globally, then fills gaps with
    defaults/repair fallbacks in itinerary order.
    """
    index = get_image_bank_index(image_bank_path)
    if not index.candidates:
        return {day: None for day in (grouped_days or {})}

    matches = {day: None for day in (grouped_days or {})}
    used_paths = {str(Path(path).resolve()) for path in (used_paths or set())}
    contexts: dict[str, dict] = {}
    candidates_by_day: dict[str, list[ImageCandidate]] = {}
    destination_payloads: list[dict] = []
    default_payloads: list[dict] = []

    for day, rows in (grouped_days or {}).items():
        context = build_day_context(day, rows)
        candidates = list(index.candidates_for_context(context))
        contexts[day] = context
        candidates_by_day[day] = candidates
        for candidate in candidates:
            payload = _candidate_payload_for_global_assignment(day, context, candidate, candidates, used_paths)
            if payload is None:
                continue
            (default_payloads if payload.get("is_default") else destination_payloads).append(payload)

    _assign_payloads_globally(matches, destination_payloads, used_paths)
    _assign_payloads_globally(matches, default_payloads, used_paths)

    for day in (grouped_days or {}):
        if matches.get(day) is not None:
            continue
        match = select_best_candidate_for_context(day, contexts[day], candidates_by_day[day], used_paths)
        matches[day] = match
        if match and "reused strong default" not in str(match.get("reason", "")).lower():
            used_paths.add(str(Path(match["path"]).resolve()))
    return matches


