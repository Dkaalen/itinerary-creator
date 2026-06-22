"""Image-bank diagnostics, quality-gate status, and coverage helpers."""

from pathlib import Path

from images.remote_distribution import DestinationRequest, destination_requests_from_rows, image_bank_manifest_url, schedule_destination_prefetch
from images.scanner import get_image_bank_index
from images.image_bank_discovery import coerce_and_dedupe_paths, get_image_bank_paths, get_image_bank_scan_paths
from images.image_bank_settings import clean_space, image_bank_repo_branch, image_bank_repo_url, repo_zip_url, runtime_bootstrap_allowed


def image_bank_status_for_paths(paths) -> dict:
    """Return image-bank status for a concrete path list."""

    scan_paths = coerce_and_dedupe_paths(paths)
    index = get_image_bank_index(scan_paths)
    candidates = index.candidates
    destination_candidates = index.destination_candidates
    default_candidates = index.defaults
    destination_paths = list(index.destination_roots)

    countries = list(index.countries)
    destinations = list(index.destinations)
    full_bank_found = bool(destination_candidates)
    default_only = bool(default_candidates) and not full_bank_found
    missing_full_bank = not full_bank_found
    blocking_message = ""
    if missing_full_bank:
        blocking_message = (
            "Full destination image bank is missing. Add Pictures is currently using only the bundled Default bank; "
            "connect the separate Dkaalen/itinerary-image-bank repository before approving final pictures."
        )

    return {
        "paths": [str(path) for path in scan_paths],
        "existing_paths": [str(path) for path in scan_paths if path.exists() and path.is_dir()],
        "source_path": destination_paths[0] if destination_paths else "",
        "destination_source_paths": destination_paths,
        "repo_url": image_bank_repo_url(),
        "branch": image_bank_repo_branch(),
        "zip_url": repo_zip_url(),
        "manifest_url": image_bank_manifest_url(),
        "full_bank_found": full_bank_found,
        "using_full_destination_bank": full_bank_found,
        "missing_full_bank": missing_full_bank,
        "default_only": default_only,
        "is_default_only": default_only,
        "destination_image_count": len(destination_candidates),
        "default_image_count": len(default_candidates),
        "total_image_count": len(candidates),
        "countries_found": countries,
        "destinations_found": destinations,
        "runtime_bootstrap_allowed": runtime_bootstrap_allowed(),
        "blocking_message": blocking_message,
        "warnings": [blocking_message] if blocking_message else [],
    }


def destination_coverage(index, requests: list[DestinationRequest]) -> tuple[list[str], list[str]]:
    covered: list[str] = []
    missing: list[str] = []
    for request in requests:
        candidates = list(index.candidates_for_city(request.destination, include_defaults=False))
        if request.country:
            country_key = clean_space(request.country).casefold()
            candidates = [candidate for candidate in candidates if clean_space(candidate.country).casefold() == country_key]
        (covered if candidates else missing).append(request.key)
    return covered, missing


def image_bank_status(root=None, required_destinations=None) -> dict:
    """Return operational image-bank status for diagnostics and quality gates."""

    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    status = image_bank_status_for_paths(get_image_bank_paths(root))
    requests = destination_requests_from_rows(required_destinations)
    if not requests:
        status["required_destinations_ready"] = bool(status.get("full_bank_found"))
        status["required_destinations"] = []
        status["covered_destinations"] = []
        status["missing_destinations"] = []
        return status

    index = get_image_bank_index(get_image_bank_paths(root))
    covered, missing = destination_coverage(index, requests)
    status["required_destinations"] = [request.key for request in requests]
    status["covered_destinations"] = covered
    status["missing_destinations"] = missing
    status["required_destinations_ready"] = not missing
    if missing:
        status["blocking_message"] = (
            "Destination pictures are not ready for: " + ", ".join(missing) + ". "
            "The app will download only these destination packs from the separate image bank."
        )
        status["warnings"] = [status["blocking_message"]]
    return status


def prefetch_image_bank_for_rows(rows_or_grouped_days, root=None) -> bool:
    """Start destination-pack prefetch after parsing without blocking the UI."""

    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    if not runtime_bootstrap_allowed():
        return False
    return schedule_destination_prefetch(root, rows_or_grouped_days)


def infer_country_for_city(city, root=None):
    city_key = clean_space(city).lower()
    index = get_image_bank_index(get_image_bank_scan_paths(root))
    for candidate in index.candidates_for_city(city, include_defaults=False):
        if clean_space(candidate.city).lower() == city_key and candidate.country:
            return candidate.country
    return "Custom"
