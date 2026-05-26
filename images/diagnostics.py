"""Image-bank diagnostics and debug formatting."""

from __future__ import annotations

from pathlib import Path

from .fallback import is_global_default_candidate
from .scanner import coerce_image_bank_paths, scan_image_bank


def get_image_bank_diagnostics(image_bank_path: Path | str | list | tuple | set = "image_bank") -> dict:
    """Return lightweight scan diagnostics for the app sidebar/debug panels."""
    paths = coerce_image_bank_paths(image_bank_path)
    candidates = scan_image_bank(paths)
    default_images = [candidate for candidate in candidates if is_global_default_candidate(candidate)]
    destination_images = [candidate for candidate in candidates if not is_global_default_candidate(candidate)]
    by_city: dict[str, int] = {}
    by_country: dict[str, int] = {}
    for candidate in candidates:
        city_key = candidate.city or "Default"
        country_key = candidate.country or "Global"
        by_city[city_key] = by_city.get(city_key, 0) + 1
        by_country[country_key] = by_country.get(country_key, 0) + 1

    return {
        "paths": [str(path) for path in paths],
        "existing_paths": [str(path) for path in paths if path.exists() and path.is_dir()],
        "total_images": len(candidates),
        "default_images": len(default_images),
        "destination_images": len(destination_images),
        "by_city": dict(sorted(by_city.items(), key=lambda item: item[0].lower())),
        "by_country": dict(sorted(by_country.items(), key=lambda item: item[0].lower())),
    }


def format_match_for_debug(match: dict | None) -> str:
    if not match:
        return "No suitable image found"
    return f"{match['path']} — score {match['score']} ({match['reason']})"
