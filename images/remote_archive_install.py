"""Archive download, validation, and atomic install for remote image packs."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import tempfile
import time
import urllib.request
import uuid
import zipfile

from images.remote_distribution_config import DOWNLOAD_CHUNK_SIZE, IMAGE_EXTENSIONS, network_timeout_seconds
from images.remote_distribution_models import DistributionError, ResolvedDestinationPack
from images.remote_distribution_requests import atomic_write_json, request


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(DOWNLOAD_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_archive(pack: ResolvedDestinationPack, archive_path: Path) -> None:
    if archive_path.is_file() and sha256_file(archive_path) == pack.sha256:
        return
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_name(f".{archive_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(request(pack.download_url), timeout=network_timeout_seconds()) as response:
            with temporary.open("wb") as output:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
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


def validated_member_path(member_name: str) -> PurePosixPath:
    member = PurePosixPath(member_name.replace("\\", "/"))
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise DistributionError(f"Unsafe path in destination image pack: {member_name!r}.")
    if member.parts[0] != "image_bank_full":
        raise DistributionError(f"Unexpected root in destination image pack: {member_name!r}.")
    return member


def install_archive(pack: ResolvedDestinationPack, archive_path: Path, version_root: Path) -> Path:
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
                member = validated_member_path(info.filename)
                if Path(member.name).suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                target = staging_root.joinpath(*member.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=DOWNLOAD_CHUNK_SIZE)

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

        atomic_write_json(marker_path, {
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


def cleanup_old_versions(root: Path, active_version: str, keep: int = 2) -> None:
    versions_root = root / "versions"
    if not versions_root.is_dir():
        return
    candidates = [path for path in versions_root.iterdir() if path.is_dir() and path.name != active_version]
    candidates.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    for stale in candidates[max(0, keep - 1):]:
        shutil.rmtree(stale, ignore_errors=True)
