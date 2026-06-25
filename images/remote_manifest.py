"""Destination-pack installation orchestration for remote image-bank distribution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Sequence
from pathlib import Path
from typing import Any
import json
import time

from images.remote_archive_install import cleanup_old_versions, download_archive, install_archive
from images.remote_distribution_config import ACTIVE_MANIFEST_NAME, distribution_root, download_workers, image_bank_manifest_url
from images.remote_distribution_locking import file_lock
from images.remote_distribution_models import DestinationRequest, ResolvedDestinationPack
from images.remote_distribution_requests import atomic_write_json, load_distribution_manifest
from images.remote_pack_resolver import destination_requests_from_rows, resolve_destination_packs


def ensure_destination_packs(
    app_root: Path,
    requests: Sequence[DestinationRequest] | Any,
    *,
    force_manifest_refresh: bool = False,
) -> dict[str, Any]:
    """Install all requested destination packs and activate their bank version."""

    normalized_requests = destination_requests_from_rows(requests)
    if not normalized_requests:
        return {
            "ok": False,
            "code": "no_destination_requests",
            "message": "No itinerary destinations were available for image-bank download.",
            "method": "destination_packs",
            "path": "",
            "requested_destinations": [],
        }

    root = distribution_root(app_root)
    lock_path = root / ".locks" / "distribution.lock"
    with file_lock(lock_path):
        manifest, manifest_status = load_distribution_manifest(app_root, force_refresh=force_manifest_refresh)
        resolved, unresolved = resolve_destination_packs(manifest, normalized_requests)
        bank_version = str(manifest["bank_version"])
        version_root = root / "versions" / bank_version
        archives_root = root / "archives"

        installed: list[ResolvedDestinationPack] = []
        errors: list[str] = []

        def install(pack: ResolvedDestinationPack) -> ResolvedDestinationPack:
            archive_path = archives_root / f"{pack.sha256}.zip"
            download_archive(pack, archive_path)
            install_archive(pack, archive_path, version_root)
            return pack

        if resolved:
            with ThreadPoolExecutor(max_workers=min(download_workers(), len(resolved))) as executor:
                future_map = {executor.submit(install, pack): pack for pack in resolved}
                for future in as_completed(future_map):
                    pack = future_map[future]
                    try:
                        installed.append(future.result())
                    except Exception as error:  # keep independent destinations usable
                        errors.append(f"{pack.destination}: {type(error).__name__}: {error}")

        bank_path = version_root / "image_bank_full"
        if installed and bank_path.is_dir():
            existing_installed: set[str] = set()
            active_path = root / ACTIVE_MANIFEST_NAME
            try:
                active_payload = json.loads(active_path.read_text(encoding="utf-8"))
                if str(active_payload.get("bank_version") or "") == bank_version:
                    existing_installed.update(
                        str(value) for value in (active_payload.get("installed_destinations") or []) if value
                    )
            except (OSError, ValueError, TypeError):
                pass
            existing_installed.update(f"{pack.country}/{pack.destination}" for pack in installed)
            atomic_write_json(root / ACTIVE_MANIFEST_NAME, {
                "schema_version": 1,
                "bank_version": bank_version,
                "source_commit": str(manifest.get("source_commit") or ""),
                "activated_at": int(time.time()),
                "installed_destinations": sorted(existing_installed, key=str.casefold),
            })
            cleanup_old_versions(root, bank_version)
            from images.scanner import invalidate_image_bank_cache

            invalidate_image_bank_cache(bank_path)

        unresolved_names = [request.key for request in unresolved]
        installed_names = sorted({f"{pack.country}/{pack.destination}" for pack in installed}, key=str.casefold)
        ok = bool(resolved) and not errors and not unresolved and len(installed) == len(resolved)
        if ok:
            code = "destination_packs_ready"
            message = f"Downloaded or reused {len(installed)} destination image pack(s)."
        elif installed:
            code = "destination_packs_partial"
            message = "Some destination image packs could not be prepared."
        else:
            code = "destination_packs_failed"
            message = "No required destination image packs could be prepared."

        return {
            "ok": ok,
            "code": code,
            "message": message,
            "method": "destination_packs",
            "path": str(bank_path if bank_path.is_dir() else ""),
            "manifest_url": image_bank_manifest_url(),
            "manifest_source": manifest_status.get("source", ""),
            "manifest_stale": bool(manifest_status.get("stale")),
            "manifest_network_error": manifest_status.get("network_error", ""),
            "bank_version": bank_version,
            "requested_destinations": [request.key for request in normalized_requests],
            "resolved_destinations": [pack.manifest_key for pack in resolved],
            "installed_destinations": installed_names,
            "unresolved_destinations": unresolved_names,
            "errors": errors,
        }
