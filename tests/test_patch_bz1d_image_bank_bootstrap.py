from __future__ import annotations

import os
import inspect
import zipfile
from pathlib import Path

import diagnostics
from PIL import Image

from images import image_bank
from images import remote_distribution
from images.remote_distribution import (
    DestinationRequest,
    DistributionError,
    ResolvedDestinationPack,
)


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 16), (20, 80, 120)).save(path, format="WEBP")


def _runtime_paths(root: Path) -> tuple[Path, Path]:
    return image_bank._runtime_bank_paths(root)


def _failure(code: str, message: str, *, method: str, error: str) -> dict:
    return image_bank._setup_status(
        False,
        code,
        message,
        method=method,
        error=error,
        warn=False,
    )


def test_bz1d_bootstrap_configuration_never_sniffs_pytest(monkeypatch):
    monkeypatch.delenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test-name")

    assert image_bank._runtime_bootstrap_allowed() is True

    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "0")
    assert image_bank._runtime_bootstrap_allowed() is False
    assert "PYTEST_CURRENT_TEST" not in inspect.getsource(image_bank._runtime_bootstrap_allowed)


def test_bz1d_git_success_has_stable_attempt_diagnostics(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    _runtime_repo, runtime_bank = _runtime_paths(root)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")

    def fetch_git(*_args):
        _write_webp(runtime_bank / "Norway" / "Oslo" / "oslo.webp")
        return image_bank._setup_status(
            True,
            "fetched_git",
            "Fetched with git.",
            path=runtime_bank,
            method="git",
            source="git",
        )

    monkeypatch.setattr(image_bank, "_fetch_image_bank_with_git", fetch_git)
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_zip",
        lambda *_args: (_ for _ in ()).throw(AssertionError("ZIP fallback must not run")),
    )

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is True
    assert status["source"] == "git"
    assert status["git_attempted"] is True
    assert status["zip_attempted"] is False
    assert status["fallback_used"] is False
    assert status["diagnostic_code"] == "fetched_git"


def test_bz1d_git_failure_zip_success_reports_real_fallback(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    _runtime_repo, runtime_bank = _runtime_paths(root)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_git",
        lambda *_args: _failure(
            "git_command_failed",
            "Git failed.",
            method="git",
            error="TimeoutExpired: clone timed out",
        ),
    )

    def fetch_zip(*_args):
        _write_webp(runtime_bank / "Norway" / "Bergen" / "bergen.webp")
        return image_bank._setup_status(
            True,
            "fetched_zip",
            "Fetched with ZIP.",
            path=runtime_bank,
            method="zip",
            source="zip",
            fallback_used=True,
        )

    monkeypatch.setattr(image_bank, "_fetch_image_bank_with_zip", fetch_zip)

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is True
    assert status["source"] == "zip"
    assert status["fallback_used"] is True
    assert status["fallback_from"] == "git_command_failed"
    assert status["git_attempted"] is True
    assert status["zip_attempted"] is True
    assert "TimeoutExpired" in status["git_error"]
    assert status["zip_error"] == ""


def test_bz1d_complete_remote_failure_never_reports_success(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_git",
        lambda *_args: _failure("git_command_failed", "Git failed.", method="git", error="git timeout"),
    )
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_zip",
        lambda *_args: _failure("zip_download_failed", "ZIP failed.", method="zip", error="HTTP timeout"),
    )
    diagnostics.reset()

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is False
    assert status["code"] == "zip_download_failed"
    assert status["cache_available"] is False
    assert status["git_error"] == "git timeout"
    assert status["zip_error"] == "HTTP timeout"
    assert status["fallback_used"] is True
    warnings = [entry for entry in diagnostics.get_warnings() if entry["category"] == "image_bank_setup"]
    assert len(warnings) == 1


def test_bz1d_disabled_bootstrap_uses_valid_cache_without_network(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    _runtime_repo, runtime_bank = _runtime_paths(root)
    _write_webp(runtime_bank / "Norway" / "Oslo" / "oslo.webp")
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "0")
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_git",
        lambda *_args: (_ for _ in ()).throw(AssertionError("network must remain disabled")),
    )

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is True
    assert status["code"] == "cached_bootstrap_disabled"
    assert status["source"] == "cache"
    assert status["cache_available"] is True
    assert status["git_attempted"] is False
    assert status["zip_attempted"] is False


def test_bz1d_disabled_bootstrap_without_cache_is_explicit_failure(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "off")

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is False
    assert status["code"] == "bootstrap_disabled"
    assert status["source"] == "disabled"
    assert status["cache_available"] is False


def test_bz1d_corrupt_cache_is_never_accepted(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    _runtime_repo, runtime_bank = _runtime_paths(root)
    corrupt = runtime_bank / "Norway" / "Oslo" / "corrupt.webp"
    corrupt.parent.mkdir(parents=True)
    corrupt.write_bytes(b"not-an-image")
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "0")

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is False
    assert status["code"] == "bootstrap_disabled"
    assert status["cache_available"] is False


def test_bz1d_valid_cache_can_be_used_after_remote_failure(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    _runtime_repo, runtime_bank = _runtime_paths(root)
    _write_webp(runtime_bank / "Norway" / "Oslo" / "oslo.webp")
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    cache_results = iter([None, runtime_bank])
    monkeypatch.setattr(image_bank, "_cached_bank_for_requests", lambda *_args: next(cache_results))
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_git",
        lambda *_args: _failure("git_returned_error", "Git failed.", method="git", error="exit 1"),
    )
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_zip",
        lambda *_args: _failure("zip_download_failed", "ZIP failed.", method="zip", error="offline"),
    )

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is True
    assert status["code"] == "cached_after_remote_failure"
    assert status["source"] == "cache"
    assert status["degraded"] is True
    assert status["cache_available"] is True
    assert status["git_error"] == "exit 1"
    assert status["zip_error"] == "offline"


def test_bz1d_distribution_exception_is_preserved_through_final_failure(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr(
        image_bank,
        "ensure_destination_packs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(DistributionError("lock timeout")),
    )
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_git",
        lambda *_args: _failure("git_missing", "Git missing.", method="git", error="not installed"),
    )
    monkeypatch.setattr(
        image_bank,
        "_fetch_image_bank_with_zip",
        lambda *_args: _failure("zip_download_failed", "ZIP failed.", method="zip", error="offline"),
    )

    status = image_bank.ensure_runtime_image_bank_status(
        root,
        required_destinations=[DestinationRequest("Oslo", "Norway")],
    )

    assert status["ok"] is False
    assert status["distribution_attempted"] is True
    assert "DistributionError: lock timeout" in status["distribution_error"]
    assert status["git_attempted"] is True
    assert status["zip_attempted"] is True


def test_bz1d_zip_rejects_unsafe_archive_members(monkeypatch, tmp_path):
    runtime_repo = tmp_path / "runtime" / "itinerary-image-bank"
    runtime_bank = runtime_repo / "image_bank_full"

    def fake_urlretrieve(_url, filename):
        with zipfile.ZipFile(filename, "w") as archive:
            archive.writestr("../image_bank_full/Norway/Oslo/escape.webp", b"bad")
        return filename, None

    monkeypatch.setattr(image_bank.urllib.request, "urlretrieve", fake_urlretrieve)

    status = image_bank._fetch_image_bank_with_zip(runtime_repo, runtime_bank)

    assert status["ok"] is False
    assert status["code"] == "zip_extract_failed"
    assert "Unsafe path" in status["zip_error"]
    assert not (tmp_path / "image_bank_full").exists()


def test_bz1d_zip_disk_failure_is_reported(monkeypatch, tmp_path):
    runtime_repo = tmp_path / "runtime" / "itinerary-image-bank"
    runtime_bank = runtime_repo / "image_bank_full"

    def fake_urlretrieve(_url, filename):
        Path(filename).write_bytes(b"placeholder")
        return filename, None

    monkeypatch.setattr(image_bank.urllib.request, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(
        image_bank,
        "_extract_full_bank_archive",
        lambda *_args: (_ for _ in ()).throw(OSError("disk full")),
    )

    status = image_bank._fetch_image_bank_with_zip(runtime_repo, runtime_bank)

    assert status["ok"] is False
    assert status["code"] == "zip_extract_failed"
    assert "disk full" in status["zip_error"]


def test_bz1d_zip_atomic_install_rolls_back_existing_bank(monkeypatch, tmp_path):
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


def test_bz1d_zip_failed_rollback_retains_recovery_backup(monkeypatch, tmp_path):
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


def test_bz1d_destination_pack_failed_rollback_retains_recovery_backup(monkeypatch, tmp_path):
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


def test_bz1d_distribution_lock_timeout_is_deterministic(monkeypatch, tmp_path):
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
