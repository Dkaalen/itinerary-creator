from __future__ import annotations

import diagnostics

from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_planner import DayPlan
from itinerary_generation.day_titles import create_day_title
from itinerary_generation.title_brain import write_day_title
from project_storage.file_writer import best_effort_cleanup
from scripts.test_groups import GROUPS, missing_group_paths


def test_day_planner_discards_legacy_intro_snippets() -> None:
    plan = DayPlan("travel_day", title="Travel to Bergen", intro="After check-in, old prose.")

    assert plan.intro == ""
    assert "legacy_planner_intro_discarded" in plan.warnings


def test_day_title_facade_delegates_to_title_brain() -> None:
    rows = [
        {"day": "Day 1", "type": "Transfer", "city": "Bergen", "title": "Self transfer to Bergen Airport"},
        {"day": "Day 1", "type": "Flight", "city": "Bergen", "title": "Flight from Bergen to Tromsø"},
        {"day": "Day 1", "type": "Hotel", "city": "Tromsø", "title": "Check in to your accommodation"},
        {"day": "Day 1", "type": "Activity", "city": "Tromsø", "title": "Northern Lights Cruise"},
    ]

    assert create_day_title(rows) == write_day_title(rows)


def test_day_facts_is_backed_by_focused_submodules() -> None:
    facts = build_day_facts([
        {"type": "Arrival", "city": "Oslo", "title": "Arrival in Oslo"},
        {"type": "Hotel", "city": "Oslo", "title": "Check in to your accommodation"},
        {"type": "Leisure", "city": "Oslo", "title": "Spend time at leisure"},
    ])

    assert facts.main_city == "Oslo"
    assert facts.has_accommodation is True
    assert facts.partial_leisure_day is True


def test_quality_group_owns_day_brain_regressions() -> None:
    quality = set(GROUPS["quality"])

    assert "tests/test_day_brain_copy.py" in quality
    assert "tests/test_day_brain_intelligence.py" in quality
    assert "tests/test_day_brain_proof_hardening.py" in quality
    assert "tests/test_day_sub_brains.py" in quality


def test_missing_group_paths_accepts_pytest_node_ids(tmp_path) -> None:
    repo = tmp_path
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")

    from scripts import test_groups

    old_groups = test_groups.GROUPS
    try:
        test_groups.GROUPS = {"example": ("tests/test_example.py::test_ok",)}  # type: ignore[assignment]
        assert missing_group_paths(repo) == ()
    finally:
        test_groups.GROUPS = old_groups  # type: ignore[assignment]


class _BrokenCleanupRepository:
    def delete_storage_files(self, paths):
        raise RuntimeError("storage cleanup failed")

    def delete_version(self, version_id):
        raise RuntimeError("version cleanup failed")


def test_best_effort_cleanup_records_observable_warnings() -> None:
    diagnostics.reset()

    best_effort_cleanup(_BrokenCleanupRepository(), storage_path="projects/demo.json", version_id="v1")

    warnings = diagnostics.get_warnings()
    assert len(warnings) == 2
    assert {warning["category"] for warning in warnings} == {"project_storage_cleanup"}
    assert all(warning["source"] == "project_storage.file_writer" for warning in warnings)
