"""Replacement image option helpers for the visual editor."""

from __future__ import annotations

from pathlib import Path

from image_matcher import build_day_context, candidate_to_payload, score_image_for_day
from images.scanner import get_image_bank_index
from images.image_bank import clean_space, image_bank_status_for_paths, normalize_path_key


def list_replacement_image_options(city, *, image_bank_scan_paths, allow_default_options=False):
    """Return replacement pictures for a city.

    Bundled Default images are emergency placeholders.  When the full
    destination bank is missing, do not flood the editor with defaults; surface
    the image-bank warning instead and return no replacement options.
    """
    status = image_bank_status_for_paths(image_bank_scan_paths)
    if status.get("missing_full_bank"):
        return []
    city_key = clean_space(city).lower()
    city_options = []
    default_options = []
    seen = set()
    index = get_image_bank_index(image_bank_scan_paths)
    for candidate in index.candidates_for_city(city, include_defaults=allow_default_options):
        path = Path(candidate.path)
        key = normalize_path_key(path)
        if key in seen:
            continue
        candidate_city = clean_space(candidate.city).lower()
        if city_key and candidate_city == city_key:
            city_options.append(path)
            seen.add(key)
        elif candidate_city == "default" and allow_default_options:
            default_options.append(path)
            seen.add(key)
    return sorted(city_options, key=lambda path: path.name.lower()) + sorted(default_options, key=lambda path: path.name.lower())


def list_replacement_image_options_for_rows(day, rows, limit=30, *, image_bank_scan_paths, allow_default_options=False):
    """Return lightweight, relevance-ranked replacement options for a day.

    The returned items intentionally contain no base64 image payload. The visual
    editor receives labels and paths only, preventing replacement lists from
    sending the full image bank to the browser.
    """
    status = image_bank_status_for_paths(image_bank_scan_paths)
    if status.get("missing_full_bank"):
        return []
    index = get_image_bank_index(image_bank_scan_paths)
    if not index.candidates:
        return []
    context = build_day_context(day, rows or [])
    candidates = index.candidates_for_context(context, include_defaults=allow_default_options)
    scored = []
    seen = set()
    for candidate in candidates:
        path = Path(candidate.path)
        key = normalize_path_key(path)
        if key in seen:
            continue
        score, reasons = score_image_for_day(candidate, context)
        if score <= 0:
            continue
        payload = candidate_to_payload(day, candidate, score, reasons)
        if payload.get("is_default") and not allow_default_options:
            continue
        breakdown = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else {}
        priority = (
            0 if payload.get("is_default") else 1,
            int(breakdown.get("destination_score") or 0),
            int(breakdown.get("season_score") or 0),
            int(breakdown.get("activity_product_score") or 0),
            int(score or 0),
            candidate.filename.lower(),
        )
        scored.append((priority, score, candidate, reasons))
        seen.add(key)
    scored.sort(key=lambda item: item[0], reverse=True)
    options = []
    for _priority, score, candidate, reasons in scored[:limit]:
        path = Path(candidate.path)
        options.append({
            "path": str(path),
            "name": path.name,
            "score": score,
            "reason": "; ".join(reasons or []),
            "themes": list(candidate.themes),
            "seasons": list(candidate.seasons),
            "city": candidate.city,
        })
    return options


