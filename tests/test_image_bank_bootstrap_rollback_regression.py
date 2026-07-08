from __future__ import annotations

import os
import zipfile
from pathlib import Path

from PIL import Image

from images import image_bank
from images import remote_distribution
from images.remote_distribution import (
    DistributionError,
    ResolvedDestinationPack,
)


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 16), (20, 80, 120)).save(path, format="WEBP")


def test_zip_atomic_install_rolls_back_existing_bank(monkeypatch, tmp_path):
    runtime_repo = tmp_path / "runtime" / "itinerary-image-bank"
    runtime_bank = runtime_repo / "image_bank_full"
    old_image = runtime_bank / "Norway" / "Oslo" / "old.webp"
    _write_webp(old_image)

    def fake_urlretrieve(_url, filename):
        source = tmp_path / "new.webp"
        _write_webp(source)
        with zipfile.ZipFile(filename, "w") as archive:
            archive.write(source, "itinerary-image-bank-main/image_bank_full/Norway/Bergen/new.webp")
        return filename, None

    real_replace = os.replace
    failed_install = False

    def fail_install_once(source, destination):
        nonlocal failed_install
        source_path = Path(source)
        destination_path = Path(destination)
        if not failed_install and destination_path == runtime_repo and source_path.name.startswith(".image-bank-full-"):
            failed_install = True
            raise OSError("atomic install failed")
        return real_replace(source, destination)

    monkeypatch.setattr(image_bank.urllib.request, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(image_bank.os, "replace", fail_install_once)

    status = image_bank._fetch_image_bank_with_zip(runtime_repo, runtime_bank)

    assert status["ok"] is False
    assert status["code"] == "zip_extract_failed"
    assert "atomic install failed" in status["zip_error"]
    assert old_image.exists()
    assert not (runtime_bank / "Norway" / "Bergen" / "new.webp").exists()


def test_zip_failed_rollback_retains_recovery_backup(monkeypatch, tmp_path):
    runtime_repo = tmp_path / "runtime" / "itinerary-image-bank"
    runtime_bank = runtime_repo / "image_bank_full"
    old_image = runtime_bank / "Norway" / "Oslo" / "old.webp"
    _write_webp(old_image)

    def fake_urlretrieve(_url, filename):
        source = tmp_path / "new.webp"
        _write_webp(source)
        with zipfile.ZipFile(filename, "w") as archive:
            archive.write(source, "itinerary-image-bank-main/image_bank_full/Norway/Bergen/new.webp")
        return filename, None

    real_replace = os.replace

    def fail_install_and_rollback(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if destination_path == runtime_repo and (
            source_path.name.startswith(".image-bank-full-")
            or source_path.name.startswith(".itinerary-image-bank.backup-")
        ):
            raise OSError("replacement unavailable")
        return real_replace(source, destination)

    monkeypatch.setattr(image_bank.urllib.request, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(image_bank.os, "replace", fail_install_and_rollback)

    status = image_bank._fetch_image_bank_with_zip(runtime_repo, runtime_bank)

    backups = list(runtime_repo.parent.glob(".itinerary-image-bank.backup-*"))
    assert status["ok"] is False
    assert "backup was retained" in status["zip_error"]
    assert len(backups) == 1
    assert (backups[0] / "image_bank_full" / "Norway" / "Oslo" / "old.webp").exists()


def test_destination_pack_failed_rollback_retains_recovery_backup(monkeypatch, tmp_path):
    version_root = tmp_path / "versions" / "bank-v1"
    destination_dir = version_root / "image_bank_full" / "Norway" / "Oslo"
    old_image = destination_dir / "old.webp"
    _write_webp(old_image)
    source = tmp_path / "new.webp"
    _write_webp(source)
    archive_path = tmp_path / "oslo.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(source, "image_bank_full/Norway/Oslo/new.webp")

    pack = ResolvedDestinationPack(
        manifest_key="Norway/Oslo",
        country="Norway",
        destination="Oslo",
        asset_name="norway-oslo.zip",
        download_url="https://example.test/norway-oslo.zip",
        sha256="0" * 64,
        file_count=1,
        size_bytes=archive_path.stat().st_size,
    )
    real_replace = os.replace

    def fail_install_and_rollback(source_path, destination_path):
        source_path = Path(source_path)
        destination_path = Path(destination_path)
        if destination_path == destination_dir and (
            ".staging" in source_path.parts
            or source_path.name.startswith(".Oslo.backup-")
        ):
            raise OSError("destination replacement unavailable")
        return real_replace(source_path, destination_path)

    monkeypatch.setattr(remote_distribution.os, "replace", fail_install_and_rollback)

    try:
        remote_distribution._install_archive(pack, archive_path, version_root)
    except DistributionError as error:
        assert "backup was retained" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected DistributionError")

    backups = list(destination_dir.parent.glob(".Oslo.backup-*"))
    assert len(backups) == 1
    assert (backups[0] / "old.webp").exists()


def test_distribution_lock_timeout_is_deterministic(monkeypatch, tmp_path):
    lock_path = tmp_path / "distribution.lock"
    lock_path.write_text("busy", encoding="utf-8")
    monkeypatch.setattr(remote_distribution, "_lock_timeout_seconds", lambda: 0.0)

    try:
        with remote_distribution._file_lock(lock_path):
            raise AssertionError("lock should not be acquired")
    except DistributionError as error:
        assert "Timed out waiting" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected DistributionError")
