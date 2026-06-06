"""Image-bank diagnostics and debug formatting."""

from __future__ import annotations

from pathlib import Path

from .fallback import is_global_default_candidate
from .image_bank import image_bank_status_for_paths
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

    status = image_bank_status_for_paths(paths)
    return {
        "paths": [str(path) for path in paths],
        "existing_paths": [str(path) for path in paths if path.exists() and path.is_dir()],
        "total_images": len(candidates),
        "default_images": len(default_images),
        "destination_images": len(destination_images),
        "by_city": dict(sorted(by_city.items(), key=lambda item: item[0].lower())),
        "by_country": dict(sorted(by_country.items(), key=lambda item: item[0].lower())),
        "full_bank_found": status.get("full_bank_found", False),
        "source_path": status.get("source_path", ""),
        "countries_found": status.get("countries_found", []),
        "destinations_found": status.get("destinations_found", []),
        "blocking_message": status.get("blocking_message", ""),
        "repo_url": status.get("repo_url", ""),
        "zip_url": status.get("zip_url", ""),
    }


def image_bank_status_summary(status: dict | None) -> str:
    """Return a concise operational status string for image-bank UI/logs."""

    status = status or {}
    if status.get("full_bank_found"):
        return (
            f"Full image bank: {status.get('destination_image_count', 0)} destination images "
            f"across {len(status.get('destinations_found', []) or [])} destinations"
        )
    if status.get("blocking_message"):
        return str(status.get("blocking_message"))
    return "Image-bank status unavailable"


def image_bank_debug_payload(image_bank_path: Path | str | list | tuple | set = "image_bank") -> dict:
    """Return a copyable diagnostic payload for support/debugging."""

    diagnostics = get_image_bank_diagnostics(image_bank_path)
    return {
        "paths": diagnostics.get("paths", []),
        "existing_paths": diagnostics.get("existing_paths", []),
        "full_bank_found": diagnostics.get("full_bank_found", False),
        "source_path": diagnostics.get("source_path", ""),
        "total_images": diagnostics.get("total_images", 0),
        "destination_images": diagnostics.get("destination_images", 0),
        "default_images": diagnostics.get("default_images", 0),
        "countries_found": diagnostics.get("countries_found", []),
        "destinations_found_sample": (diagnostics.get("destinations_found", []) or [])[:25],
        "blocking_message": diagnostics.get("blocking_message", ""),
        "repo_url": diagnostics.get("repo_url", ""),
        "zip_url": diagnostics.get("zip_url", ""),
    }


def format_match_for_debug(match: dict | None) -> str:
    if not match:
        return "No suitable image found"
    breakdown = match.get("score_breakdown") if isinstance(match.get("score_breakdown"), dict) else {}
    breakdown_text = ""
    if breakdown:
        breakdown_text = (
            f" | destination {breakdown.get('destination_score', 0)}, "
            f"activity {breakdown.get('activity_product_score', 0)}, "
            f"season {breakdown.get('season_score', 0)}, "
            f"country/region {breakdown.get('country_region_score', 0)}"
        )
    return f"{match.get('path', '')} — score {match.get('score', 0)} ({match.get('reason', '')}){breakdown_text}"
