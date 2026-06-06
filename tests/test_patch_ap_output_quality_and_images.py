from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import create_journey_arc, group_rows_by_day
from images import image_bank
from images.matcher_selection import select_day_images
from itinerary_generation.quality_gate import evaluate_client_output_quality
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "real_inputs" / "nordic_patch_ap_quality_input.txt"
WEAK_OUTPUT_MARKERS = (
    "Flight connection",
    "onward train",
    "onward connection",
    "onward connections",
    "Travel continues",
    "Continue your journey with arranged travel connected",
)


def _fixture_rows() -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(FIXTURE.read_text(encoding="utf-8")))


def test_patch_ap_real_fixture_journey_arc_uses_destination_welcome_not_travel_filler():
    rows = _fixture_rows()
    grouped = group_rows_by_day(rows)
    arc = create_journey_arc(grouped)
    arc_by_chapter = {row["chapter"]: row["experience"] for row in arc}
    arc_text = "\n".join(row["experience"] for row in arc)

    assert arc_by_chapter["Bergen"] == "Welcome to Bergen"
    assert arc_by_chapter["Helsinki"] == "Tallinn Old Town day trip"
    for marker in WEAK_OUTPUT_MARKERS:
        assert marker.lower() not in arc_text.lower()


def test_patch_ap_real_fixture_day_intros_use_experience_or_welcome_copy():
    rows = _fixture_rows()
    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {})
    days = {day.day: day for day in context.render_document.days}

    assert days["Day 2"].title == "Day Excursion to Tallinn"
    assert "Tallinn" in days["Day 2"].intro
    assert "historic Old Town" in days["Day 2"].intro
    assert "onward" not in days["Day 2"].intro.lower()

    assert days["Day 6"].title == "Northern Lights Chase"
    assert days["Day 6"].intro.startswith("Welcome to Tromsø.")
    assert "Travel continues" not in days["Day 6"].intro

    assert days["Day 8"].title == "Welcome to Bergen"
    assert days["Day 8"].intro.startswith("Welcome to Bergen.")
    assert "Flight connection" not in days["Day 8"].intro

    report = evaluate_client_output_quality(context.render_document)
    codes = {issue.code for issue in report.blocking_issues}
    assert "weak_journey_arc_flight_connection" not in codes
    assert "weak_travel_continues" not in codes
    assert not report.blocking_issues


def test_patch_ap_image_bank_runtime_bootstrap_is_default_last_resort(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    fallback = root / "image_bank"
    fallback.mkdir(parents=True)
    (fallback / "Default").mkdir()

    runtime_bank = root / image_bank.RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank" / "image_bank_full"

    def fake_run(cmd, **kwargs):
        runtime_bank.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (20, 20), (1, 2, 3)).save(runtime_bank / "dummy.webp", format="WEBP")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.delenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(subprocess, "run", fake_run)

    paths = image_bank.get_image_bank_paths(root)

    assert paths[0] == runtime_bank
    assert fallback in paths


def test_patch_ap_image_bank_bootstrap_can_be_disabled(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    fallback = root / "image_bank"
    fallback.mkdir(parents=True)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "0")

    def fail_if_called(*args, **kwargs):  # pragma: no cover
        raise AssertionError("bootstrap should be disabled")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    assert image_bank.get_image_bank_paths(root) == [fallback]


def test_patch_ap_default_images_lose_when_destination_bank_has_matches(tmp_path):
    bank = tmp_path / "image_bank_full"
    (bank / "Norway" / "Bergen").mkdir(parents=True)
    (bank / "Norway" / "Tromsø").mkdir(parents=True)
    (bank / "Default").mkdir(parents=True)
    Image.new("RGB", (40, 25), (20, 80, 120)).save(bank / "Norway" / "Bergen" / "Bergen_Autumn_City_01.webp", format="WEBP")
    Image.new("RGB", (40, 25), (20, 80, 120)).save(bank / "Norway" / "Tromsø" / "Tromso_Northern_Lights_Autumn_01.webp", format="WEBP")
    Image.new("RGB", (40, 25), (80, 80, 80)).save(bank / "Default" / "Default_Autumn_City_01.webp", format="WEBP")

    rows = _fixture_rows()
    grouped = {day: day_rows for day, day_rows in group_rows_by_day(rows).items() if day in {"Day 6", "Day 8"}}
    matches = select_day_images(grouped, bank)

    assert matches["Day 6"]["city"] == "Tromsø"
    assert matches["Day 6"]["is_default"] is False
    assert matches["Day 8"]["city"] == "Bergen"
    assert matches["Day 8"]["is_default"] is False
