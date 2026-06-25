"""Manifest network and cache helpers for remote image-bank distribution."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from threading import Lock
from typing import Any
import json
import os
import time
import urllib.error
import urllib.request
import uuid

from images.remote_distribution_config import (
    MANIFEST_CACHE_NAME,
    MAX_MANIFEST_BYTES,
    DOWNLOAD_CHUNK_SIZE,
    distribution_root,
    image_bank_manifest_url,
    manifest_ttl_seconds,
    network_timeout_seconds,
    SUPPORTED_SCHEMA_VERSIONS,
)
from images.remote_distribution_models import DistributionError

MANIFEST_LOCK = Lock()


def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": "itinerary-creator-image-bank/1",
            "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.8",
        },
    )


def read_limited_response(response, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(DOWNLOAD_CHUNK_SIZE, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise DistributionError("Remote image-bank manifest exceeded the safety size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_manifest(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise DistributionError("Remote image-bank manifest is not a JSON object.")
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise DistributionError(f"Unsupported image-bank manifest schema: {schema_version!r}.")
    bank_version = str(payload.get("bank_version") or "").strip()
    destinations = payload.get("destinations")
    if not bank_version or not isinstance(destinations, Mapping) or not destinations:
        raise DistributionError("Remote image-bank manifest is missing bank_version or destinations.")
    return dict(payload)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def load_distribution_manifest(app_root: Path, *, force_refresh: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the release manifest with a persistent stale-on-error cache."""

    root = distribution_root(app_root)
    cache_path = root / MANIFEST_CACHE_NAME
    ttl = manifest_ttl_seconds()

    with MANIFEST_LOCK:
        if cache_path.is_file() and not force_refresh:
            try:
                age = max(0.0, time.time() - cache_path.stat().st_mtime)
                if age <= ttl:
                    manifest = validate_manifest(json.loads(cache_path.read_text(encoding="utf-8")))
                    return manifest, {"source": "cache", "stale": False, "age_seconds": age}
            except (OSError, ValueError, TypeError, DistributionError):
                pass

        network_error = ""
        try:
            with urllib.request.urlopen(request(image_bank_manifest_url()), timeout=network_timeout_seconds()) as response:
                raw = read_limited_response(response, MAX_MANIFEST_BYTES)
            manifest = validate_manifest(json.loads(raw.decode("utf-8")))
            atomic_write_json(cache_path, manifest)
            return manifest, {"source": "network", "stale": False, "age_seconds": 0.0}
        except (OSError, UnicodeError, ValueError, TypeError, urllib.error.URLError, DistributionError) as error:
            network_error = f"{type(error).__name__}: {error}"

        if cache_path.is_file():
            try:
                manifest = validate_manifest(json.loads(cache_path.read_text(encoding="utf-8")))
                age = max(0.0, time.time() - cache_path.stat().st_mtime)
                return manifest, {
                    "source": "stale_cache",
                    "stale": True,
                    "age_seconds": age,
                    "network_error": network_error,
                }
            except (OSError, ValueError, TypeError, DistributionError):
                pass

        raise DistributionError(f"Could not load the remote image-bank manifest. {network_error}".strip())
