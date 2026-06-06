from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from images import image_bank
from images.image_match_audit import audit_day_image_matches
from images.matcher_selection import select_day_image
from itinerary_generation.quality_gate import evaluate_client_output_quality


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 20), (20, 80, 120)).save(path, format="WEBP")


def test_patch_ar_image_bank_status_identifies_full_destination_bank(tmp_path):
    bank = tmp_path / "image_bank_full"
    _write_webp(bank / "Norway" / "Oslo" / "Oslo_Autumn_City_01.webp")
    _write_webp(bank / "Default" / "Default_Autumn_City_01.webp")

    status = image_bank.image_bank_status_for_paths([bank])

    assert status["full_bank_found"] is True
    assert status["missing_full_bank"] is False
    assert status["destination_image_count"] == 1
    assert status["default_image_count"] == 1
    assert status["source_path"] == str(bank)
    assert status["countries_found"] == ["Norway"]
    assert status["destinations_found"] == ["Oslo"]


def test_patch_ar_default_only_bank_is_blocking_status(tmp_path):
    bank = tmp_path / "image_bank"
    _write_webp(bank / "Default" / "Default_Autumn_City_01.webp")

    status = image_bank.image_bank_status_for_paths([bank])

    assert status["full_bank_found"] is False
    assert status["missing_full_bank"] is True
    assert status["default_only"] is True
    assert status["destination_image_count"] == 0
    assert "Full destination image bank is missing" in status["blocking_message"]


def test_patch_ar_audit_blocks_default_only_bank_before_pdf_export(tmp_path):
    bank = tmp_path / "image_bank"
    image_path = bank / "Default" / "Default_Autumn_City_01.webp"
    _write_webp(image_path)

    grouped = {
        "Day 1": [
            {
                "day": "Day 1",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Oslo",
                "title": "Oslo Walking Tour",
                "details": "City landmarks and waterfront.",
            }
        ]
    }
    matches = {"Day 1": {"path": str(image_path), "city": "Default", "is_default": True, "reason": "fallback"}}

    warnings = audit_day_image_matches(grouped, matches, image_bank_scan_paths=[bank])

    assert any(warning.code == "image_bank_full_missing" for warning in warnings)
    assert any(warning.severity == "error" for warning in warnings)


def test_patch_ar_client_quality_gate_blocks_missing_full_image_bank(tmp_path):
    bank = tmp_path / "image_bank"
    _write_webp(bank / "Default" / "Default_Autumn_City_01.webp")
    status = image_bank.image_bank_status_for_paths([bank])

    report = evaluate_client_output_quality(
        SimpleNamespace(days=[], final_sections=[]),
        image_bank_status=status,
    )

    assert report.is_blocked
    assert any(issue.code == "image_bank_full_missing" for issue in report.blocking_issues)


def test_patch_ar_image_path_lookup_does_not_clone_runtime_repo(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    fallback = root / "image_bank"
    fallback.mkdir(parents=True)

    def fail_if_called(*args, **kwargs):  # pragma: no cover
        raise AssertionError("get_image_bank_paths must not clone or pull repositories")

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(subprocess, "run", fail_if_called)

    assert image_bank.get_image_bank_paths(root) == [fallback]


def test_patch_ar_explicit_runtime_setup_fetches_image_bank(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    fallback = root / "image_bank"
    fallback.mkdir(parents=True)
    runtime_bank = root / image_bank.RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank" / "image_bank_full"

    def fake_run(cmd, **kwargs):
        _write_webp(runtime_bank / "Norway" / "Bergen" / "Bergen_Autumn_City_01.webp")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr(image_bank.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(subprocess, "run", fake_run)

    fetched = image_bank.ensure_runtime_image_bank(root)

    assert fetched == runtime_bank
    assert image_bank.get_image_bank_paths(root)[0] == runtime_bank


def test_patch_ar_selected_image_audit_contains_country_region_score(tmp_path):
    bank = tmp_path / "image_bank_full"
    _write_webp(bank / "Norway" / "Oslo" / "Oslo_Autumn_City_01.webp")

    match = select_day_image(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "05/11/2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Oslo",
                "title": "Oslo Walking Tour",
                "details": "Guided city walk by the waterfront.",
            }
        ],
        bank,
    )

    assert match
    breakdown = match["score_breakdown"]
    assert breakdown["destination_score"] > 0
    assert breakdown["country_region_score"] > 0
    assert breakdown["total_score"] == match["score"]
