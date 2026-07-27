from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.test_catalogue import (
    assert_unique_stage_targets,
    catalogue_lines,
    duplicate_stage_targets,
    validate_test_catalogue,
)
from scripts.test_group_catalog import GROUPS, GROUP_ORDER, TEST_STAGE_BOUNDARY_SECONDS
from scripts.test_runner_manifest import build_test_plan
from scripts.test_runner_models import TestPlanSpec, TestStageSpec
from scripts.test_runner_state import build_summary, new_checkpoint
from scripts.test_suite_audit import DEFAULT_JSON, DEFAULT_MD


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MAJOR_DOMAIN_GROUPS = {
    "architecture",
    "calculator",
    "generator",
    "routes",
    "inclusions",
    "quality",
    "export",
    "editor",
    "storage",
    "images",
    "failure-modes",
}


def test_catalogue_is_complete_valid_and_deterministic() -> None:
    first = validate_test_catalogue(ROOT)
    second = validate_test_catalogue(ROOT)

    assert first.valid
    assert first == second
    assert first.uncatalogued_modules == ()
    assert set(first.discovered_modules) == set(first.registered_modules)
    assert tuple(GROUPS) == GROUP_ORDER
    assert REQUIRED_MAJOR_DOMAIN_GROUPS.issubset(GROUPS)
    assert catalogue_lines("architecture") == catalogue_lines("architecture")


def test_catalogue_rejects_missing_duplicate_and_uncatalogued_modules(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_registered.py").write_text("def test_registered(): pass\n", encoding="utf-8")
    (tests_dir / "test_uncatalogued.py").write_text("def test_uncatalogued(): pass\n", encoding="utf-8")
    groups = {
        "broken": (
            "tests/test_registered.py",
            "tests/test_registered.py",
            "tests/test_missing.py",
        )
    }

    report = validate_test_catalogue(tmp_path, groups=groups, group_order=("broken",))
    codes = {issue.code for issue in report.issues}

    assert not report.valid
    assert "duplicate_group_target" in codes
    assert "missing_test_module" in codes
    assert "uncatalogued_test_module" in codes
    assert report.uncatalogued_modules == ("test_uncatalogued.py",)


def test_executable_plans_reject_exact_duplicate_targets() -> None:
    duplicate = TestStageSpec("one", "one", ("python", "-V"), 10, targets=("tests/test_a.py",))
    duplicate_again = TestStageSpec("two", "two", ("python", "-V"), 10, targets=("tests/test_a.py",))

    assert duplicate_stage_targets((duplicate, duplicate_again)) == ("tests/test_a.py",)
    with pytest.raises(ValueError, match="duplicate target"):
        assert_unique_stage_targets((duplicate, duplicate_again))


def test_all_supported_plans_are_bounded_and_duplicate_free() -> None:
    for plan_name in (*GROUP_ORDER, "health", "release", "full", "proof"):
        plan = build_test_plan(plan_name)
        assert plan.stages
        assert all(1 <= stage.timeout_seconds <= TEST_STAGE_BOUNDARY_SECONDS for stage in plan.stages)
        assert all(stage.group_id for stage in plan.stages)
        assert duplicate_stage_targets(plan.stages) == ()


def test_summary_records_elapsed_time_and_boundary_by_group() -> None:
    stage = TestStageSpec(
        stage_id="stage",
        label="stage",
        command=(sys.executable, "-V"),
        timeout_seconds=TEST_STAGE_BOUNDARY_SECONDS,
        group_id="quality",
    )
    plan = TestPlanSpec("summary", "summary", (stage,))
    checkpoint = new_checkpoint(plan)
    checkpoint["stages"][stage.stage_id] = {
        "status": "PASS",
        "elapsed_seconds": TEST_STAGE_BOUNDARY_SECONDS + 0.5,
        "log_path": "stage.log",
    }

    summary = build_summary(plan, checkpoint, {stage.stage_id})

    assert summary["stages"][0]["boundary_exceeded"] is True
    assert summary["groups"] == [
        {
            "group_id": "quality",
            "elapsed_seconds": TEST_STAGE_BOUNDARY_SECONDS + 0.5,
            "stage_count": 1,
            "passed": 1,
            "failed": 0,
            "timed_out": 0,
            "not_run": 0,
            "boundary_exceeded_stages": 1,
        }
    ]



def test_standalone_test_entrypoints_share_the_45_second_boundary() -> None:
    from scripts.run_release_candidate import DEFAULT_STEP_TIMEOUT_SECONDS
    from scripts.run_slow_tests import TEST_TIMEOUT_SECONDS
    from scripts.test_runner_execution import DEFAULT_STAGE_TIMEOUT_SECONDS

    assert DEFAULT_STEP_TIMEOUT_SECONDS <= TEST_STAGE_BOUNDARY_SECONDS
    assert TEST_TIMEOUT_SECONDS <= TEST_STAGE_BOUNDARY_SECONDS
    assert DEFAULT_STAGE_TIMEOUT_SECONDS <= TEST_STAGE_BOUNDARY_SECONDS

    health_source = (ROOT / "scripts" / "run_health_check.py").read_text(encoding="utf-8")
    worker_source = (ROOT / "scripts" / "run_pytest_stage.py").read_text(encoding="utf-8")
    direct_source = (ROOT / "scripts" / "run_test_function_direct.py").read_text(encoding="utf-8")

    assert "run_controlled_process" in health_source
    assert "timeout_seconds=TEST_STAGE_BOUNDARY_SECONDS" in health_source
    assert "min(args.timeout_seconds, TEST_STAGE_BOUNDARY_SECONDS)" in worker_source
    assert "min(args.timeout_seconds, TEST_STAGE_BOUNDARY_SECONDS)" in direct_source

def test_catalogue_listing_does_not_run_tests_or_write_tracked_reports(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/test_catalogue.py", "--list", "--group", "architecture"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.stdout.startswith("architecture (")
    output = completed.stdout.lower()
    assert " passed in " not in output
    assert " collected in " not in output
    assert not (tmp_path / ".test-runs").exists()
    assert ".test-runs" in str(DEFAULT_MD)
    assert ".test-runs" in str(DEFAULT_JSON)
