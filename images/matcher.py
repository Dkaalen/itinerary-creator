"""Destination-first image matching and day-image selection."""

from __future__ import annotations

from pathlib import Path

from .fallback import is_global_default_candidate, score_default_candidate
from .metadata import (
    ImageCandidate,
    SEASON_ALIASES,
    city_variants,
    infer_season_from_rows,
    infer_themes,
    normalize_keyword,
    tokenize,
)
from .scanner import scan_image_bank


def _row_type(row: dict) -> str:
    return normalize_keyword(row.get("effective_type") or row.get("type") or "")


def _row_text(row: dict) -> str:
    return " ".join([
        str(row.get("city", "") or ""),
        str(row.get("title", "") or ""),
        str(row.get("original_title", "") or ""),
        str(row.get("details", "") or ""),
        str(row.get("display_description", "") or ""),
        " ".join(row.get("includes", []) or []),
    ])


def _themes_for_rows(rows: list[dict]) -> set[str]:
    text_parts = []
    hinted = set()
    for row in rows or []:
        row_type = _row_type(row)
        row_text = _row_text(row)
        row_tokens = tokenize(row_text)
        text_parts.append(row_text)
        if row_type in {"hotel", "accommodation", "arrival", "departure"}:
            hinted.add("city")
        if row_type in {"transfer", "transport"}:
            if row_tokens & {"train", "rail", "railway", "express", "overnight"}:
                hinted.add("train")
            if row_tokens & {"coach", "bus", "road", "route", "drive", "panorama"}:
                hinted.add("road journey")
    tokens = tokenize(" ".join(text_parts))
    return infer_themes(tokens) | hinted


def build_day_context(day: str, rows: list[dict]) -> dict:
    city = ""
    parts = [day]
    for row in rows or []:
        if not city and str(row.get("city", "")).strip():
            city = str(row.get("city", "")).strip()
        parts.append(_row_text(row))

    non_transport_rows = [
        row for row in (rows or [])
        if _row_type(row) not in {"transfer", "transport"}
    ]
    primary_rows = non_transport_rows or list(rows or [])

    text = " ".join(parts)
    tokens = tokenize(text)
    themes = infer_themes(tokens) | _themes_for_rows(rows or [])
    primary_themes = _themes_for_rows(primary_rows)
    return {
        "day": day,
        "city": city,
        "city_variants": city_variants(city),
        "tokens": tokens,
        "themes": themes,
        "primary_themes": primary_themes,
        "season": infer_season_from_rows(rows),
        "text": normalize_keyword(text),
    }


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
    day_themes = set(day_context.get("themes", set()))
    day_city_variants = set(day_context.get("city_variants", set()))

    candidate_city_variants = city_variants(candidate.city)
    filename_city_variants = city_variants(candidate.filename)

    if is_global_default_candidate(candidate):
        return score_default_candidate(candidate, day_context)

    if not day_city_variants or not (candidate_city_variants & day_city_variants):
        return 0, ["no destination match"]

    score += 60
    reasons.append("city folder match")

    if filename_city_variants & day_city_variants:
        score += 20
        reasons.append("city filename match")

    theme_matches = candidate_themes & day_themes
    if theme_matches:
        score += 18 * len(theme_matches)
        reasons.append("theme match: " + ", ".join(sorted(theme_matches)))

    day_season = normalize_keyword(day_context.get("season", ""))
    candidate_seasons = set(candidate.seasons)
    if day_season and day_season in candidate_seasons:
        score += 12
        reasons.append(f"season match: {day_season}")

    token_matches = (candidate_tokens & day_tokens) - day_city_variants - set(SEASON_ALIASES)
    if token_matches:
        score += min(20, 4 * len(token_matches))
        reasons.append("keyword match: " + ", ".join(sorted(list(token_matches))[:5]))

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


# Backwards-compatible private aliases for callers/tests that may have imported them.
_candidate_destination_matches = candidate_destination_matches
_season_available_for_context = season_available_for_context
_candidate_to_payload = candidate_to_payload
_select_best_candidate_for_context = select_best_candidate_for_context
