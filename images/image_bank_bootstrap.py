"""Runtime image-bank bootstrap orchestration."""

from pathlib import Path
from typing import Callable

import diagnostics

from images.remote_distribution import DestinationRequest, destination_requests_from_rows, ensure_destination_packs
from images.scanner import get_image_bank_index, invalidate_image_bank_cache
from images.image_bank_bootstrap_status import merge_attempts, normalise_stage_status, setup_status, stage_error
from images.image_bank_discovery import runtime_bank_paths, valid_persistent_cache
from images.image_bank_settings import APP_ROOT, runtime_bootstrap_allowed
from images.image_bank_status import destination_coverage, image_bank_status

FetchFn = Callable[[Path, Path], dict]
DestinationPackFn = Callable[..., dict]
CachedBankFn = Callable[[Path, list[DestinationRequest]], Path | None]


def cached_bank_for_requests(root: Path, requests: list[DestinationRequest]) -> Path | None:
    """Return a valid persistent cache that covers all requested destinations."""

    _runtime_repo, runtime_bank = runtime_bank_paths(root)
    from images.remote_distribution import active_distribution_bank

    candidates = [active_distribution_bank(root), runtime_bank]
    for candidate in candidates:
        if candidate is None or not valid_persistent_cache(candidate):
            continue
        if not requests:
            return candidate
        index = get_image_bank_index([candidate])
        _covered, missing = destination_coverage(index, requests)
        if not missing:
            return candidate
    return None


def ensure_runtime_image_bank_status(
    root: Path | str | None = None,
    required_destinations=None,
    *,
    fetch_git: FetchFn,
    fetch_zip: FetchFn,
    cached_bank: CachedBankFn = cached_bank_for_requests,
    destination_pack_fetcher: DestinationPackFn = ensure_destination_packs,
) -> dict:
    """Explicitly fetch/update the runtime image bank and return diagnostics."""

    root = Path(root) if root is not None else APP_ROOT
    destination_requests = destination_requests_from_rows(required_destinations)
    runtime_repo, runtime_bank = runtime_bank_paths(root)
    cached = cached_bank(root, destination_requests)

    if not runtime_bootstrap_allowed():
        if cached is not None:
            return setup_status(
                True,
                "cached_bootstrap_disabled",
                "Runtime image-bank fetching is disabled; a valid cached image bank will be used.",
                path=cached,
                method="cache",
                source="cache",
                cache_available=True,
            )
        return setup_status(
            False,
            "bootstrap_disabled",
            "Runtime image-bank fetching is disabled. Set ITINERARY_IMAGE_BANK_FULL or enable ITINERARY_IMAGE_BANK_BOOTSTRAP.",
            method="disabled",
        )

    if cached is not None:
        return setup_status(
            True,
            "already_available",
            "A valid persistent image bank is already connected.",
            path=cached,
            method="existing",
            source="cache",
            cache_available=True,
        )

    try:
        runtime_repo.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return setup_status(
            False,
            "runtime_dir_failed",
            "Could not create the runtime image-bank folder.",
            error=f"{type(error).__name__}: {error}",
            method="filesystem",
        )

    distribution_status = None
    if destination_requests:
        try:
            distribution_status = destination_pack_fetcher(root, destination_requests)
            should_refresh_manifest = bool(
                distribution_status.get("manifest_stale")
                or distribution_status.get("unresolved_destinations")
                or any(
                    "checksum mismatch" in str(error).casefold()
                    for error in (distribution_status.get("errors") or [])
                )
            )
            if not distribution_status.get("ok") and should_refresh_manifest:
                refreshed_status = destination_pack_fetcher(
                    root,
                    destination_requests,
                    force_manifest_refresh=True,
                )
                refreshed_status["initial_attempt"] = distribution_status
                distribution_status = refreshed_status
        except Exception as error:
            distribution_status = setup_status(
                False,
                "destination_pack_exception",
                "Destination image packs could not be prepared; full-bank fallback will be attempted.",
                error=f"{type(error).__name__}: {error}",
                method="destination_packs",
                warn=False,
            )
        distribution_status = normalise_stage_status(distribution_status, "destination_packs")
        if distribution_status.get("ok"):
            invalidate_image_bank_cache()
            return merge_attempts(distribution_status, distribution_status=distribution_status)

    git_status = normalise_stage_status(fetch_git(runtime_repo, runtime_bank), "git")
    if git_status.get("ok"):
        invalidate_image_bank_cache()
        return merge_attempts(
            git_status,
            distribution_status=distribution_status,
            git_status=git_status,
        )

    zip_status = normalise_stage_status(fetch_zip(runtime_repo, runtime_bank), "zip")
    if zip_status.get("ok"):
        invalidate_image_bank_cache()
        return merge_attempts(
            zip_status,
            distribution_status=distribution_status,
            git_status=git_status,
            zip_status=zip_status,
        )

    cached_after_failure = cached_bank(root, destination_requests)
    if cached_after_failure is not None:
        cached_status = setup_status(
            True,
            "cached_after_remote_failure",
            "Remote image-bank refresh failed; a valid persistent cache will be used.",
            path=cached_after_failure,
            method="cache",
            source="cache",
            fallback_used=True,
            degraded=True,
            cache_available=True,
        )
        return merge_attempts(
            cached_status,
            distribution_status=distribution_status,
            git_status=git_status,
            zip_status=zip_status,
        )

    final_status = dict(zip_status)
    final_status["ok"] = False
    final_status["cache_available"] = False
    final_status["degraded"] = False
    final_status["error"] = stage_error(zip_status)
    final_status = merge_attempts(
        final_status,
        distribution_status=distribution_status,
        git_status=git_status,
        zip_status=zip_status,
    )
    diagnostics.warn(
        "image_bank_setup",
        final_status.get("message", "Runtime image-bank setup failed."),
        final_status.get("error", ""),
        source="images.image_bank",
    )
    return final_status


def connect_remote_image_bank_if_missing(
    root: Path | str | None = None,
    required_destinations=None,
    *,
    ensure_status: Callable[..., dict],
) -> dict:
    """Connect the separate remote image-bank repo when no full bank is visible."""

    root = Path(root) if root is not None else APP_ROOT
    requests = destination_requests_from_rows(required_destinations)
    current = image_bank_status(root, required_destinations=requests)
    if current.get("required_destinations_ready", current.get("full_bank_found")):
        current["setup_status"] = setup_status(
            True,
            "already_connected",
            "Full destination image bank is already connected.",
            path=Path(current.get("source_path") or ""),
            method="existing",
        )
        return current

    setup = ensure_status(root, required_destinations=requests)
    updated = image_bank_status(root, required_destinations=requests)
    updated["setup_status"] = setup
    return updated
