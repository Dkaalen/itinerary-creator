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


def test_bootstrap_configuration_never_sniffs_pytest(monkeypatch):
    monkeypatch.delenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test-name")

    assert image_bank._runtime_bootstrap_allowed() is True

    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "0")
    assert image_bank._runtime_bootstrap_allowed() is False
    assert "PYTEST_CURRENT_TEST" not in inspect.getsource(image_bank._runtime_bootstrap_allowed)


def test_git_success_has_stable_attempt_diagnostics(monkeypatch, tmp_path):
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


def test_git_failure_zip_success_reports_real_fallback(monkeypatch, tmp_path):
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


def test_complete_remote_failure_never_reports_success(monkeypatch, tmp_path):
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


def test_disabled_bootstrap_uses_valid_cache_without_network(monkeypatch, tmp_path):
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


def test_disabled_bootstrap_without_cache_is_explicit_failure(monkeypatch, tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "off")

    status = image_bank.ensure_runtime_image_bank_status(root)

    assert status["ok"] is False
    assert status["code"] == "bootstrap_disabled"
    assert status["source"] == "disabled"
    assert status["cache_available"] is False


def test_corrupt_cache_is_never_accepted(monkeypatch, tmp_path):
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


def test_valid_cache_can_be_used_after_remote_failure(monkeypatch, tmp_path):
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


def test_distribution_exception_is_preserved_through_final_failure(monkeypatch, tmp_path):
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


def test_zip_rejects_unsafe_archive_members(monkeypatch, tmp_path):
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


def test_zip_disk_failure_is_reported(monkeypatch, tmp_path):
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
