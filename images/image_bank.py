"""Public image-bank path, bootstrap, and diagnostics facade.

The implementation is split across focused modules, while this facade keeps the
legacy import and monkeypatch surface stable for the app and regression tests.
"""

from pathlib import Path
import os
import shutil
import subprocess
import urllib.error
import urllib.request

from images.remote_distribution import (
    DestinationRequest,
    active_distribution_bank,
    destination_requests_from_rows,
    ensure_destination_packs,
    image_bank_manifest_url,
    schedule_destination_prefetch,
)
from images.scanner import coerce_image_bank_paths, get_image_bank_index, invalidate_image_bank_cache, scan_image_bank
from images.image_bank_bootstrap import (
    cached_bank_for_requests as _bootstrap_cached_bank_for_requests,
    connect_remote_image_bank_if_missing as _connect_remote_image_bank_if_missing,
    ensure_runtime_image_bank_status as _bootstrap_ensure_runtime_image_bank_status,
)
from images.image_bank_bootstrap_status import (
    ImageBankBootstrapResult,
    merge_attempts as _merge_attempts,
    normalise_stage_status as _normalise_stage_status,
    setup_status as _setup_status,
    stage_error as _stage_error,
)
from images.image_bank_discovery import (
    candidate_external_image_bank_paths as _candidate_external_image_bank_paths,
    dedupe_existing_paths as _dedupe_existing_paths,
    get_image_bank_path,
    get_image_bank_paths,
    get_image_bank_scan_paths,
    is_default_city as _is_default_city,
    looks_like_unpopulated_submodule as _looks_like_unpopulated_submodule,
    normalize_path_key,
    runtime_bank_paths as _runtime_bank_paths,
    slugify_filename,
    valid_image_bank as _valid_image_bank,
    valid_persistent_cache as _valid_persistent_cache,
)
from images.image_bank_fetch import (
    extract_full_bank_archive as _extract_full_bank_archive,
    fetch_image_bank_with_git,
    fetch_image_bank_with_zip,
)
from images.image_bank_settings import (
    APP_ROOT,
    DEFAULT_IMAGE_BANK_REPO_BRANCH,
    DEFAULT_IMAGE_BANK_REPO_URL,
    RUNTIME_IMAGE_BANK_DIR,
    SUPPORTED_IMAGE_EXTENSIONS,
    clean_space,
    esc,
    image_bank_repo_branch,
    image_bank_repo_url,
    repo_zip_url as _repo_zip_url,
    runtime_bootstrap_allowed as _runtime_bootstrap_allowed,
)
from images.image_bank_status import (
    destination_coverage as _destination_coverage,
    image_bank_status,
    image_bank_status_for_paths,
    infer_country_for_city,
    prefetch_image_bank_for_rows,
)


def _fetch_image_bank_with_git(runtime_repo: Path, runtime_bank: Path) -> dict:
    return fetch_image_bank_with_git(
        runtime_repo,
        runtime_bank,
        shutil_module=shutil,
        subprocess_module=subprocess,
    )


def _fetch_image_bank_with_zip(runtime_repo: Path, runtime_bank: Path) -> dict:
    return fetch_image_bank_with_zip(
        runtime_repo,
        runtime_bank,
        os_module=os,
        shutil_module=shutil,
        urllib_request_module=urllib.request,
        urllib_error_module=urllib.error,
        extract_archive=_extract_full_bank_archive,
    )


def _cached_bank_for_requests(root: Path, requests: list[DestinationRequest]) -> Path | None:
    return _bootstrap_cached_bank_for_requests(root, requests)


def ensure_runtime_image_bank_status(
    root: Path | str | None = None,
    required_destinations=None,
) -> dict:
    return _bootstrap_ensure_runtime_image_bank_status(
        root,
        required_destinations=required_destinations,
        fetch_git=_fetch_image_bank_with_git,
        fetch_zip=_fetch_image_bank_with_zip,
        cached_bank=_cached_bank_for_requests,
        destination_pack_fetcher=ensure_destination_packs,
    )


def connect_remote_image_bank_if_missing(
    root: Path | str | None = None,
    required_destinations=None,
) -> dict:
    return _connect_remote_image_bank_if_missing(
        root,
        required_destinations=required_destinations,
        ensure_status=ensure_runtime_image_bank_status,
    )


def ensure_runtime_image_bank(root: Path | str | None = None, required_destinations=None) -> Path | None:
    """Compatibility wrapper returning only the fetched path when setup succeeds."""

    status = ensure_runtime_image_bank_status(root, required_destinations=required_destinations)
    return Path(status["path"]) if status.get("ok") and status.get("path") else None


__all__ = [
    "APP_ROOT",
    "DEFAULT_IMAGE_BANK_REPO_BRANCH",
    "DEFAULT_IMAGE_BANK_REPO_URL",
    "DestinationRequest",
    "ImageBankBootstrapResult",
    "RUNTIME_IMAGE_BANK_DIR",
    "SUPPORTED_IMAGE_EXTENSIONS",
    "_cached_bank_for_requests",
    "_candidate_external_image_bank_paths",
    "_dedupe_existing_paths",
    "_destination_coverage",
    "_extract_full_bank_archive",
    "_fetch_image_bank_with_git",
    "_fetch_image_bank_with_zip",
    "_is_default_city",
    "_looks_like_unpopulated_submodule",
    "_merge_attempts",
    "_normalise_stage_status",
    "_repo_zip_url",
    "_runtime_bank_paths",
    "_runtime_bootstrap_allowed",
    "_setup_status",
    "_stage_error",
    "_valid_image_bank",
    "_valid_persistent_cache",
    "active_distribution_bank",
    "clean_space",
    "coerce_image_bank_paths",
    "connect_remote_image_bank_if_missing",
    "destination_requests_from_rows",
    "ensure_destination_packs",
    "ensure_runtime_image_bank",
    "ensure_runtime_image_bank_status",
    "esc",
    "get_image_bank_index",
    "get_image_bank_path",
    "get_image_bank_paths",
    "get_image_bank_scan_paths",
    "image_bank_manifest_url",
    "image_bank_repo_branch",
    "image_bank_repo_url",
    "image_bank_status",
    "image_bank_status_for_paths",
    "infer_country_for_city",
    "invalidate_image_bank_cache",
    "normalize_path_key",
    "prefetch_image_bank_for_rows",
    "scan_image_bank",
    "schedule_destination_prefetch",
    "slugify_filename",
]
