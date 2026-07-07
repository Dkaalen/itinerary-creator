from __future__ import annotations

import importlib
from pathlib import Path

from itinerary_generation.activity_title_northern_lights import (
    looks_like_northern_lights_activity,
    northern_lights_activity_title,
)
from scripts.run_validation_proof import build_plan
from scripts.review_output_regression import review_fixture
from text_polish_modules.text_cleanup_rules import apply_case_replacements
import diagnostics

ROOT = Path(__file__).resolve().parents[1]


def test_verified_legacy_facades_stay_deleted() -> None:
    deleted = (
        "app_modules/performance_telemetry_debug.py",
        "app_modules/saved_project_storage_ui.py",
        "itinerary_generation/activity_title_patterns.py",
        "itinerary_generation/day_render_group_tour_blocks.py",
        "itinerary_generation/day_render_hotel_blocks.py",
        "itinerary_generation/day_render_leisure_blocks.py",
        "itinerary_generation/journey_arc_text_safety.py",
        "pdf_exporter_modules/renderers.py",
        "project_storage/status.py",
        "text_polish_modules/core.py",
    )
    assert [path for path in deleted if (ROOT / path).exists()] == []


def test_text_cleanup_rule_table_is_split_from_cleanup_orchestrator() -> None:
    cleanup_source = (ROOT / "text_polish_modules/text_cleanup.py").read_text(encoding="utf-8")
    rule_source = (ROOT / "text_polish_modules/text_cleanup_rules.py").read_text(encoding="utf-8")

    assert len(cleanup_source.splitlines()) < 260
    assert "PROPER_NOUN_REPLACEMENTS" not in cleanup_source
    assert "PROPER_NOUN_REPLACEMENTS" in rule_source
    assert apply_case_replacements("Funicual and south coast") == "Funicular and South Coast"


def test_activity_title_northern_lights_rules_are_split_from_core() -> None:
    core_source = (ROOT / "itinerary_generation/activity_titles_core.py").read_text(encoding="utf-8")

    assert "northern_lights_activity_title" in core_source
    assert looks_like_northern_lights_activity("northern lights cruise", "silent electric ship")
    assert northern_lights_activity_title("silent electric ship cruise under northern lights") == "Northern Lights Cruise"


def test_pdf_exporter_package_no_longer_imports_renderers_facade() -> None:
    module = importlib.import_module("pdf_exporter_modules")

    assert callable(module.render_cover_page)
    assert callable(module.render_glance_page)
    assert callable(module.render_general_page)


def test_validation_proof_plan_covers_known_uncertain_lanes() -> None:
    labels = {item["label"] for item in build_plan()}

    assert "day-brain and sub-brain regression lane" in labels
    assert "hosted generation smoke" in labels
    assert "output regression review" in labels
    assert "real Excel random quality check" in labels


def test_output_regression_review_protects_norway_sample() -> None:
    report = review_fixture()

    assert report["issue_count"] == 0
    assert report["trip_title"] == "Norway Winter Highlights"
    assert report["day_titles"]["Day 4"] == "Arrival in Tromsø & Northern Lights Cruise"


def test_recoverable_pdf_prewarm_error_is_observable() -> None:
    from pdf_exporter_modules.pdf_image_prewarm import _day_image_height_for_story

    diagnostics.reset()

    assert _day_image_height_for_story([object()], object()) is None

    warnings = diagnostics.get_warnings()
    assert any(warning["category"] == "pdf_image_prewarm" for warning in warnings)
