"""Day image matching and override selection helpers."""

from __future__ import annotations

from pathlib import Path

from image_matcher import select_day_images
from images.image_bank import normalize_path_key


def day_image_match_from_path(day, path, reason="manual selection"):
    if not path:
        return None
    path_obj = Path(path)
    return {
        "day": day,
        "path": str(path_obj),
        "score": 999,
        "reason": reason,
        "city": "",
        "country": "",
        "filename": path_obj.stem,
        "themes": [],
        "seasons": [],
        "is_default": False,
        "is_generic": False,
        "fallback_reason": "",
        "score_breakdown": {
            "destination_score": 0,
            "activity_product_score": 0,
            "season_score": 0,
            "country_region_score": 0,
            "fallback_score": 0,
            "total_score": 999,
        },
    }


def select_day_images_with_overrides(grouped_days, output_edits=None, *, app_root, image_bank_scan_paths):
    """Apply day image review choices while preserving no-reuse behavior."""

    overrides = (output_edits or {}).get("day_images", {}) or {}
    selected = {}
    used_paths = set()

    # Manual and removed choices first, so automatic selections cannot reuse a
    # picture selected by the user on another day.
    for day, rows in (grouped_days or {}).items():
        choice = overrides.get(day, {}) or {}
        mode = choice.get("mode", "auto")
        manual_path = choice.get("path", "")

        if mode == "none":
            selected[day] = None
            continue

        if mode == "manual" and manual_path:
            resolved = Path(manual_path)
            if not resolved.is_absolute():
                resolved = (app_root / resolved).resolve()
            key = normalize_path_key(resolved)
            if resolved.exists() and key not in used_paths:
                selected[day] = day_image_match_from_path(day, resolved, reason="manual image selection")
                used_paths.add(key)
            else:
                selected[day] = None

    base_matches = select_day_images(grouped_days, image_bank_scan_paths, used_paths=used_paths.copy())

    for day, rows in (grouped_days or {}).items():
        if day in selected:
            continue
        match = base_matches.get(day)
        if match:
            key = normalize_path_key(match.get("path", ""))
            allows_reuse = "reused strong default" in str(match.get("reason", "")).lower()
            if key in used_paths and not allows_reuse:
                match = None
            else:
                used_paths.add(key)
        selected[day] = match

    return selected


