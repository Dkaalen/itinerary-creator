"""Destination-aware delivery for the remote itinerary image bank.

The source repository publishes a stable manifest and one immutable ZIP archive
per destination.  This module downloads only the destinations required by the
current itinerary, verifies every archive, installs it atomically, and keeps a
persistent local cache for later sessions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from threading import Lock, Thread
from typing import Any
import hashlib
import json
import os
import shutil
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
import zipfile

from place_aliases import canonicalize_place_name, country_for_place, is_likely_service_text

DEFAULT_MANIFEST_URL = (
    "https://github.com/Dkaalen/itinerary-image-bank/releases/download/"
    "image-bank-distribution/manifest.json"
)
DISTRIBUTION_DIR_NAME = "distribution"
ACTIVE_MANIFEST_NAME = "active.json"
MANIFEST_CACHE_NAME = "manifest.json"
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})
IMAGE_EXTENSIONS = frozenset({".webp", ".jpg", ".jpeg", ".png", ".avif"})
_MAX_MANIFEST_BYTES = 25 * 1024 * 1024
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024

_MANIFEST_LOCK = Lock()
_PREFETCH_LOCK = Lock()
_PREFETCH_IN_FLIGHT: set[str] = set()


@dataclass(frozen=True, slots=True)
class DestinationRequest:
    destination: str
    country: str = ""

    @property
    def key(self) -> str:
        return f"{self.country}/{self.destination}" if self.country else self.destination


@dataclass(frozen=True, slots=True)
class ResolvedDestinationPack:
    manifest_key: str
    country: str
    destination: str
    asset_name: str
    download_url: str
    sha256: str
    file_count: int
    size_bytes: int


class DistributionError(RuntimeError):
    """Raised when a destination-pack distribution cannot be used safely."""


def image_bank_manifest_url() -> str:
    return str(os.environ.get("ITINERARY_IMAGE_BANK_MANIFEST_URL", "") or DEFAULT_MANIFEST_URL).strip()


def _normalise_lookup(value: str) -> str:
    text = str(value or "").strip().casefold()
    text = text.translate(str.maketrans({
        "ø": "o", "å": "a", "æ": "ae", "ð": "d", "þ": "th", "ł": "l",
    }))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


def _safe_float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _safe_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def distribution_root(app_root: Path) -> Path:
    override = str(os.environ.get("ITINERARY_IMAGE_BANK_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser() / DISTRIBUTION_DIR_NAME
    return app_root / ".runtime_image_bank" / DISTRIBUTION_DIR_NAME


def active_distribution_bank(app_root: Path) -> Path | None:
    root = distribution_root(app_root)
    active_path = root / ACTIVE_MANIFEST_NAME
    try:
        payload = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    bank_version = str(payload.get("bank_version") or "").strip()
    if not bank_version:
        return None
    bank = root / "versions" / bank_version / "image_bank_full"
    return bank if bank.is_dir() else None


def _coerce_request(value: Any) -> DestinationRequest | None:
    if isinstance(value, DestinationRequest):
        destination = value.destination
        country = value.country
    elif isinstance(value, Mapping):
        destination = value.get("destination") or value.get("city") or value.get("location") or ""
        country = value.get("country") or ""
    else:
        destination = value
        country = ""

    destination = canonicalize_place_name(str(destination or "").strip())
    if not destination or is_likely_service_text(destination):
        return None
    country = canonicalize_place_name(str(country or "").strip()) or country_for_place(destination)
    return DestinationRequest(destination=destination, country=str(country or "").strip())


def destination_requests_from_rows(rows_or_grouped_days: Any) -> list[DestinationRequest]:
    """Return ordered, unique day-image destinations.

    When itinerary rows are supplied, use the same day-context planner as the
    image matcher. This avoids downloading origin/intermediate cities that will
    never drive a day image. Direct destination-request objects remain accepted
    for lower-level callers and tests.
    """

    grouped_items: list[tuple[str, list[dict[str, Any]]]] = []
    direct_values: list[Any] = []

    if isinstance(rows_or_grouped_days, Mapping):
        if any(key in rows_or_grouped_days for key in ("city", "destination", "location")):
            direct_values = [rows_or_grouped_days]
        else:
            for day, value in rows_or_grouped_days.items():
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    grouped_items.append((str(day), [dict(row) for row in value if isinstance(row, Mapping)]))
    elif isinstance(rows_or_grouped_days, Sequence) and not isinstance(rows_or_grouped_days, (str, bytes, bytearray)):
        values = list(rows_or_grouped_days)
        if values and all(isinstance(value, DestinationRequest) for value in values):
            direct_values = values
        elif any(isinstance(value, Mapping) and value.get("day") for value in values):
            grouped: dict[str, list[dict[str, Any]]] = {}
            for value in values:
                if not isinstance(value, Mapping):
                    continue
                day = str(value.get("day") or "").strip() or "Day"
                grouped.setdefault(day, []).append(dict(value))
            grouped_items = list(grouped.items())
        else:
            direct_values = values
    else:
        direct_values = [rows_or_grouped_days]

    if grouped_items:
        # Local import avoids coupling distribution bootstrap to matcher startup.
        from images.matcher_context import build_day_context

        for day, rows in grouped_items:
            city = str(build_day_context(day, rows).get("city") or "").strip()
            if city:
                direct_values.append({"destination": city, "country": country_for_place(city)})

    selected: list[DestinationRequest] = []
    seen: set[tuple[str, str]] = set()
    for value in direct_values:
        request = _coerce_request(value)
        if request is None:
            continue
        key = (_normalise_lookup(request.country), _normalise_lookup(request.destination))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        selected.append(request)
    return selected


def _manifest_ttl_seconds() -> float:
    return _safe_float_env("ITINERARY_IMAGE_BANK_MANIFEST_TTL_SECONDS", 300.0, 0.0, 86400.0)


def _network_timeout_seconds() -> float:
    return _safe_float_env("ITINERARY_IMAGE_BANK_NETWORK_TIMEOUT_SECONDS", 25.0, 3.0, 180.0)


def _lock_timeout_seconds() -> float:
    return _safe_float_env("ITINERARY_IMAGE_BANK_LOCK_TIMEOUT_SECONDS", 120.0, 5.0, 600.0)


def _download_workers() -> int:
    return _safe_int_env("ITINERARY_IMAGE_BANK_DOWNLOAD_WORKERS", 4, 1, 8)


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": "itinerary-creator-image-bank/1",
            "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.8",
        },
    )


def _read_limited_response(response, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(_DOWNLOAD_CHUNK_SIZE, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise DistributionError("Remote image-bank manifest exceeded the safety size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_manifest(payload: Any) -> dict[str, Any]:
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


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def load_distribution_manifest(app_root: Path, *, force_refresh: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the release manifest with a persistent stale-on-error cache."""

    root = distribution_root(app_root)
    cache_path = root / MANIFEST_CACHE_NAME
    ttl = _manifest_ttl_seconds()

    with _MANIFEST_LOCK:
        if cache_path.is_file() and not force_refresh:
            try:
                age = max(0.0, time.time() - cache_path.stat().st_mtime)
                if age <= ttl:
                    manifest = _validate_manifest(json.loads(cache_path.read_text(encoding="utf-8")))
                    return manifest, {"source": "cache", "stale": False, "age_seconds": age}
            except (OSError, ValueError, TypeError, DistributionError):
                pass

        network_error = ""
        try:
            with urllib.request.urlopen(_request(image_bank_manifest_url()), timeout=_network_timeout_seconds()) as response:
                raw = _read_limited_response(response, _MAX_MANIFEST_BYTES)
            manifest = _validate_manifest(json.loads(raw.decode("utf-8")))
            _atomic_write_json(cache_path, manifest)
            return manifest, {"source": "network", "stale": False, "age_seconds": 0.0}
        except (OSError, UnicodeError, ValueError, TypeError, urllib.error.URLError, DistributionError) as error:
            network_error = f"{type(error).__name__}: {error}"

        if cache_path.is_file():
            try:
                manifest = _validate_manifest(json.loads(cache_path.read_text(encoding="utf-8")))
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


def _entry_aliases(entry: Mapping[str, Any], field: str) -> set[str]:
    names = {str(entry.get(field) or "")}
    aliases = entry.get(f"{field}_aliases")
    if isinstance(aliases, Sequence) and not isinstance(aliases, (str, bytes, bytearray)):
        names.update(str(value or "") for value in aliases)
    return {_normalise_lookup(value) for value in names if _normalise_lookup(value)}


def resolve_destination_packs(
    manifest: Mapping[str, Any],
    requests: Sequence[DestinationRequest],
) -> tuple[list[ResolvedDestinationPack], list[DestinationRequest]]:
    destinations = manifest.get("destinations") if isinstance(manifest, Mapping) else None
    if not isinstance(destinations, Mapping):
        raise DistributionError("Remote image-bank manifest has no destinations mapping.")

    entries: list[tuple[str, Mapping[str, Any], set[str], set[str]]] = []
    for manifest_key, raw_entry in destinations.items():
        if not isinstance(raw_entry, Mapping):
            continue
        entries.append((
            str(manifest_key),
            raw_entry,
            _entry_aliases(raw_entry, "country"),
            _entry_aliases(raw_entry, "destination"),
        ))

    resolved: list[ResolvedDestinationPack] = []
    unresolved: list[DestinationRequest] = []
    seen_assets: set[str] = set()
    for request in requests:
        destination_key = _normalise_lookup(request.destination)
        country_key = _normalise_lookup(request.country)
        destination_matches = [item for item in entries if destination_key in item[3]]
        if country_key:
            exact_matches = [item for item in destination_matches if country_key in item[2]]
            if exact_matches:
                destination_matches = exact_matches
        if len(destination_matches) != 1:
            unresolved.append(request)
            continue

        manifest_key, entry, _, _ = destination_matches[0]
        asset_name = str(entry.get("asset_name") or "").strip()
        download_url = str(entry.get("download_url") or "").strip()
        sha256 = str(entry.get("sha256") or "").strip().lower()
        if not asset_name or not download_url or len(sha256) != 64:
            unresolved.append(request)
            continue
        if asset_name in seen_assets:
            continue
        seen_assets.add(asset_name)
        resolved.append(ResolvedDestinationPack(
            manifest_key=manifest_key,
            country=str(entry.get("country") or "").strip(),
            destination=str(entry.get("destination") or "").strip(),
            asset_name=asset_name,
            download_url=download_url,
            sha256=sha256,
            file_count=int(entry.get("file_count") or 0),
            size_bytes=int(entry.get("size_bytes") or 0),
        ))
    return resolved, unresolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_DOWNLOAD_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_archive(pack: ResolvedDestinationPack, archive_path: Path) -> None:
    if archive_path.is_file() and _sha256_file(archive_path) == pack.sha256:
        return
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_name(f".{archive_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(_request(pack.download_url), timeout=_network_timeout_seconds()) as response:
            with temporary.open("wb") as output:
                while True:
                    chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    digest.update(chunk)
                    output.write(chunk)
        actual = digest.hexdigest()
        if actual != pack.sha256:
            raise DistributionError(
                f"Checksum mismatch for {pack.destination}: expected {pack.sha256}, got {actual}."
            )
        os.replace(temporary, archive_path)
    finally:
        temporary.unlink(missing_ok=True)


def _validated_member_path(member_name: str) -> PurePosixPath:
    member = PurePosixPath(member_name.replace("\\", "/"))
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise DistributionError(f"Unsafe path in destination image pack: {member_name!r}.")
    if member.parts[0] != "image_bank_full":
        raise DistributionError(f"Unexpected root in destination image pack: {member_name!r}.")
    return member


def _install_archive(pack: ResolvedDestinationPack, archive_path: Path, version_root: Path) -> Path:
    bank_root = version_root / "image_bank_full"
    destination_dir = bank_root / pack.country / pack.destination
    marker_path = version_root / ".packs" / f"{pack.asset_name}.json"

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        marker = {}
    if marker.get("sha256") == pack.sha256 and destination_dir.is_dir() and any(
        path.suffix.lower() in IMAGE_EXTENSIONS for path in destination_dir.rglob("*") if path.is_file()
    ):
        return destination_dir

    staging_parent = version_root / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=f"{pack.destination}-", dir=staging_parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member = _validated_member_path(info.filename)
                if Path(member.name).suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                target = staging_root.joinpath(*member.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=_DOWNLOAD_CHUNK_SIZE)

        staged_destination = staging_root / "image_bank_full" / pack.country / pack.destination
        installed_files = [
            path for path in staged_destination.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ] if staged_destination.is_dir() else []
        if not installed_files:
            raise DistributionError(f"Destination pack for {pack.destination} contained no supported images.")
        if pack.file_count and len(installed_files) != pack.file_count:
            raise DistributionError(
                f"Destination pack for {pack.destination} contained {len(installed_files)} images; "
                f"manifest expected {pack.file_count}."
            )

        destination_dir.parent.mkdir(parents=True, exist_ok=True)
        backup = destination_dir.with_name(f".{destination_dir.name}.backup-{uuid.uuid4().hex}")
        if destination_dir.exists():
            os.replace(destination_dir, backup)
        replacement_committed = False
        try:
            os.replace(staged_destination, destination_dir)
            replacement_committed = True
        except OSError as install_error:
            if backup.exists() and not destination_dir.exists():
                try:
                    os.replace(backup, destination_dir)
                    replacement_committed = True
                except OSError as rollback_error:
                    raise RuntimeError(
                        "Destination-pack install failed and the previous pack could not be restored; "
                        f"the backup was retained at {backup}. Install error: {install_error}. "
                        f"Rollback error: {rollback_error}."
                    ) from rollback_error
            raise
        finally:
            if replacement_committed and backup.exists():
                shutil.rmtree(backup, ignore_errors=True)

        _atomic_write_json(marker_path, {
            "asset_name": pack.asset_name,
            "country": pack.country,
            "destination": pack.destination,
            "sha256": pack.sha256,
            "file_count": len(installed_files),
            "installed_at": int(time.time()),
        })
        return destination_dir
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        if isinstance(error, DistributionError):
            raise
        raise DistributionError(f"Could not install destination pack for {pack.destination}: {error}") from error
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


@contextmanager
def _file_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _lock_timeout_seconds()
    stale_after = max(_lock_timeout_seconds() * 2.0, 300.0)
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"{os.getpid()}\n{time.time()}\n".encode("ascii"))
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > stale_after:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise DistributionError("Timed out waiting for another image-bank download to finish.")
            time.sleep(0.2)
    try:
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _cleanup_old_versions(root: Path, active_version: str, keep: int = 2) -> None:
    versions_root = root / "versions"
    if not versions_root.is_dir():
        return
    candidates = [path for path in versions_root.iterdir() if path.is_dir() and path.name != active_version]
    candidates.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    for stale in candidates[max(0, keep - 1):]:
        shutil.rmtree(stale, ignore_errors=True)


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
    with _file_lock(lock_path):
        manifest, manifest_status = load_distribution_manifest(app_root, force_refresh=force_manifest_refresh)
        resolved, unresolved = resolve_destination_packs(manifest, normalized_requests)
        bank_version = str(manifest["bank_version"])
        version_root = root / "versions" / bank_version
        archives_root = root / "archives"

        installed: list[ResolvedDestinationPack] = []
        errors: list[str] = []

        def install(pack: ResolvedDestinationPack) -> ResolvedDestinationPack:
            archive_path = archives_root / f"{pack.sha256}.zip"
            _download_archive(pack, archive_path)
            _install_archive(pack, archive_path, version_root)
            return pack

        if resolved:
            with ThreadPoolExecutor(max_workers=min(_download_workers(), len(resolved))) as executor:
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
            _atomic_write_json(root / ACTIVE_MANIFEST_NAME, {
                "schema_version": 1,
                "bank_version": bank_version,
                "source_commit": str(manifest.get("source_commit") or ""),
                "activated_at": int(time.time()),
                "installed_destinations": sorted(existing_installed, key=str.casefold),
            })
            _cleanup_old_versions(root, bank_version)
            # A prefetch may add another destination to an already-active bank
            # without changing the bank root itself. Explicit invalidation keeps
            # the matcher from serving a stale in-memory index for 30 seconds.
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


def schedule_destination_prefetch(app_root: Path, rows_or_grouped_days: Any) -> bool:
    """Start a daemon prefetch once per destination set without blocking generation."""

    requests = destination_requests_from_rows(rows_or_grouped_days)
    if not requests:
        return False
    try:
        root_key = str(app_root.resolve())
    except OSError:
        root_key = str(app_root)
    signature = root_key + "|" + "|".join(
        sorted(f"{_normalise_lookup(item.country)}/{_normalise_lookup(item.destination)}" for item in requests)
    )
    with _PREFETCH_LOCK:
        if signature in _PREFETCH_IN_FLIGHT:
            return False
        _PREFETCH_IN_FLIGHT.add(signature)

    def run() -> None:
        try:
            ensure_destination_packs(app_root, requests)
        except Exception:
            # Prefetch is opportunistic. The foreground gateway returns detailed
            # diagnostics if the user reaches picture review before it succeeds.
            pass
        finally:
            with _PREFETCH_LOCK:
                _PREFETCH_IN_FLIGHT.discard(signature)

    Thread(target=run, name="image-bank-prefetch", daemon=True).start()
    return True
