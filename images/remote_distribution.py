"""Compatibility façade for remote itinerary image-bank distribution.

The delivery pipeline is split into focused modules: models, configuration,
manifest IO, pack resolution, archive install, locking, orchestration, and
prefetching. This module preserves the historical public import surface.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os
import urllib.error
import urllib.request

from images.remote_archive_install import cleanup_old_versions as _cleanup_old_versions
from images.remote_archive_install import download_archive as _download_archive
from images.remote_archive_install import install_archive as _install_archive
from images.remote_archive_install import sha256_file as _sha256_file
from images.remote_archive_install import validated_member_path as _validated_member_path
from images.remote_distribution_config import ACTIVE_MANIFEST_NAME
from images.remote_distribution_config import DEFAULT_MANIFEST_URL
from images.remote_distribution_config import DISTRIBUTION_DIR_NAME
from images.remote_distribution_config import DOWNLOAD_CHUNK_SIZE as _DOWNLOAD_CHUNK_SIZE
from images.remote_distribution_config import IMAGE_EXTENSIONS
from images.remote_distribution_config import MANIFEST_CACHE_NAME
from images.remote_distribution_config import MAX_MANIFEST_BYTES as _MAX_MANIFEST_BYTES
from images.remote_distribution_config import SUPPORTED_SCHEMA_VERSIONS
from images.remote_distribution_config import active_distribution_bank
from images.remote_distribution_config import distribution_root
from images.remote_distribution_config import download_workers as _download_workers
from images.remote_distribution_config import image_bank_manifest_url
from images.remote_distribution_config import lock_timeout_seconds as _lock_timeout_seconds
from images.remote_distribution_config import manifest_ttl_seconds as _manifest_ttl_seconds
from images.remote_distribution_config import network_timeout_seconds as _network_timeout_seconds
from images.remote_distribution_config import normalise_lookup as _normalise_lookup
from images.remote_distribution_config import safe_float_env as _safe_float_env
from images.remote_distribution_config import safe_int_env as _safe_int_env
from images.remote_distribution_locking import file_lock
from images.remote_distribution_models import DestinationRequest, DistributionError, ResolvedDestinationPack
from images.remote_distribution_prefetch import PREFETCH_IN_FLIGHT as _PREFETCH_IN_FLIGHT
from images.remote_distribution_prefetch import PREFETCH_LOCK as _PREFETCH_LOCK
from images.remote_distribution_prefetch import schedule_destination_prefetch
from images.remote_distribution_requests import MANIFEST_LOCK as _MANIFEST_LOCK
from images.remote_distribution_requests import atomic_write_json as _atomic_write_json
from images.remote_distribution_requests import load_distribution_manifest
from images.remote_distribution_requests import read_limited_response as _read_limited_response
from images.remote_distribution_requests import request as _request
from images.remote_distribution_requests import validate_manifest as _validate_manifest
from images.remote_manifest import ensure_destination_packs
from images.remote_pack_resolver import coerce_request as _coerce_request
from images.remote_pack_resolver import destination_requests_from_rows
from images.remote_pack_resolver import entry_aliases as _entry_aliases
from images.remote_pack_resolver import resolve_destination_packs


@contextmanager
def _file_lock(lock_path: Path):
    """Compatibility wrapper whose timeout can still be monkeypatched here."""

    with file_lock(lock_path, timeout_seconds=lambda: _lock_timeout_seconds()):
        yield


__all__ = [
    "ACTIVE_MANIFEST_NAME",
    "DEFAULT_MANIFEST_URL",
    "DISTRIBUTION_DIR_NAME",
    "DestinationRequest",
    "DistributionError",
    "IMAGE_EXTENSIONS",
    "MANIFEST_CACHE_NAME",
    "ResolvedDestinationPack",
    "SUPPORTED_SCHEMA_VERSIONS",
    "active_distribution_bank",
    "destination_requests_from_rows",
    "distribution_root",
    "ensure_destination_packs",
    "image_bank_manifest_url",
    "load_distribution_manifest",
    "resolve_destination_packs",
    "schedule_destination_prefetch",
    "_MAX_MANIFEST_BYTES",
    "_DOWNLOAD_CHUNK_SIZE",
    "_MANIFEST_LOCK",
    "_PREFETCH_IN_FLIGHT",
    "_PREFETCH_LOCK",
    "_atomic_write_json",
    "_cleanup_old_versions",
    "_coerce_request",
    "_download_archive",
    "_download_workers",
    "_entry_aliases",
    "_file_lock",
    "_install_archive",
    "_lock_timeout_seconds",
    "_manifest_ttl_seconds",
    "_network_timeout_seconds",
    "_normalise_lookup",
    "_read_limited_response",
    "_request",
    "_safe_float_env",
    "_safe_int_env",
    "_sha256_file",
    "_validate_manifest",
    "_validated_member_path",
]
