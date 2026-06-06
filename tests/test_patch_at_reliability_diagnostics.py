from __future__ import annotations

import os
import subprocess
from pathlib import Path

import diagnostics
from images import image_bank_debug_payload
from images import image_bank_status_summary
from images import scanner
from images.diagnostics import format_match_for_debug
from images.image_bank import ensure_runtime_image_bank_status, image_bank_status_for_paths


def test_patch_at_scan_cache_key_tracks_nested_file_size_even_when_mtime_is_unchanged(tmp_path):
    bank = tmp_path / "image_bank_full"
    image = bank / "Norway" / "Oslo" / "Oslo_Autumn_City_01.webp"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"first")
    fixed_time = 1_700_000_000
    os.utime(image, (fixed_time, fixed_time))
    first_key = scanner._scan_cache_key(bank)

    image.write_bytes(b"second-content-is-longer")
    os.utime(image, (fixed_time, fixed_time))
    second_key = scanner._scan_cache_key(bank)

    assert first_key != second_key
    assert first_key[0][2] == second_key[0][2] == 1
    assert first_key[0][3] != second_key[0][3]


def test_patch_at_runtime_image_bank_setup_returns_failure_diagnostics(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    root.mkdir()

    def fail_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git clone", timeout=1)

    diagnostics.reset()
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr("images.image_bank.shutil.which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr("images.image_bank.subprocess.run", fail_run)

    status = ensure_runtime_image_bank_status(root)

    assert status["ok"] is False
    assert status["code"] == "git_command_failed"
    assert "Could not fetch" in status["message"]
    assert any(entry["category"] == "image_bank_setup" for entry in diagnostics.get_warnings())


def test_patch_at_image_bank_debug_payload_and_summary_are_copyable(tmp_path):
    bank = tmp_path / "image_bank_full"
    image = bank / "Norway" / "Bergen" / "Bergen_Autumn_Waterfront_01.webp"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"fake")

    status = image_bank_status_for_paths([bank])
    payload = image_bank_debug_payload([bank])

    assert "Full image bank" in image_bank_status_summary(status)
    assert payload["full_bank_found"] is True
    assert payload["destination_images"] == 1
    assert payload["destinations_found_sample"] == ["Bergen"]


def test_patch_at_match_debug_includes_score_breakdown():
    text = format_match_for_debug(
        {
            "path": "/tmp/Norway/Oslo/Oslo_Autumn_City_01.webp",
            "score": 88,
            "reason": "city folder match; season match",
            "score_breakdown": {
                "destination_score": 35,
                "activity_product_score": 12,
                "season_score": 8,
                "country_region_score": 6,
            },
        }
    )

    assert "score 88" in text
    assert "destination 35" in text
    assert "country/region 6" in text
