from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from scripts.subprocess_control import run_controlled_process
from scripts.test_runner_manifest import (
    PROOF_PLAN_NAME,
    build_test_plan,
    pytest_stage_command,
    timeout_for_stage,
)
from scripts.test_runner_models import TestPlanSpec, TestStageSpec
from scripts.test_runner_orchestrator import RunOptions, run_test_plan, selected_stage_numbers
from scripts.test_runner_state import (
    load_checkpoint,
    mark_stage_running,
    new_checkpoint,
    save_checkpoint,
    stage_log_path,
)


def _command_stage(stage_id: str, text: str = "ok") -> TestStageSpec:
    command = (sys.executable, "-c", f"print({text!r}, flush=True)")
    return TestStageSpec(
        stage_id=stage_id,
        label=stage_id,
        command=command,
        timeout_seconds=10,
        kind="command",
    )


def _plan(*stages: TestStageSpec, name: str = "unit-plan") -> TestPlanSpec:
    return TestPlanSpec(name=name, description="test plan", stages=tuple(stages))


def test_manifest_stage_ids_and_fingerprint_are_stable_and_unique() -> None:
    first = build_test_plan("full")
    second = build_test_plan("full")

    assert first.fingerprint == second.fingerprint
    assert [stage.stage_id for stage in first.stages] == [stage.stage_id for stage in second.stages]
    assert len({stage.stage_id for stage in first.stages}) == len(first.stages)


def test_full_plan_honors_timeout_safe_group_chunk_sizes() -> None:
    plan = build_test_plan("full")
    quality_stages = [stage for stage in plan.stages if stage.label.startswith("quality ")]
    fast_stages = [stage for stage in plan.stages if stage.label.startswith("fast safety ")]

    assert quality_stages
    assert fast_stages
    assert all(len(stage.targets) <= 2 for stage in quality_stages)
    assert all(len(stage.targets) <= 6 for stage in fast_stages)



def test_slow_manifest_uses_direct_function_worker() -> None:
    plan = build_test_plan("slow")

    assert plan.stages
    assert all(stage.kind == "direct-test" for stage in plan.stages)
    assert all("scripts/run_test_function_direct.py" in stage.command for stage in plan.stages)


def test_proof_plan_uses_shared_manifest() -> None:
    plan = build_test_plan(PROOF_PLAN_NAME)
    labels = {stage.label for stage in plan.stages}

    assert len(plan.stages) > 12
    assert "release truth regressions" in labels
    assert "preview PDF text parity" in labels
    assert all(stage.timeout_seconds > 0 for stage in plan.stages)



def test_proof_pytest_stages_are_sandbox_sized() -> None:
    plan = build_test_plan(PROOF_PLAN_NAME)
    pytest_stages = [stage for stage in plan.stages if stage.kind == "pytest"]

    assert pytest_stages
    assert all(1 <= len(stage.targets) <= 2 for stage in pytest_stages)

def test_timeout_policy_is_stage_local() -> None:
    assert timeout_for_stage("fast safety", ("tests/test_example.py",)) < timeout_for_stage(
        "pdf/rendering", ("tests/test_pdf_example.py",)
    )
    assert timeout_for_stage("slow 1/1", ("tests/test_fixture.py::test_large",)) <= timeout_for_stage(
        "quality", ("tests/test_real_fixture.py",)
    )


def test_pytest_stage_command_uses_diagnostic_worker() -> None:
    command = pytest_stage_command("quality", ("tests/test_example.py",), ("-k", "example"), 123)

    assert "scripts/run_pytest_stage.py" in command
    assert command[command.index("--timeout-seconds") + 1] == "123"
    assert command.index("--") < command.index("tests/test_example.py")


def test_stage_selection_supports_start_and_range(tmp_path: Path) -> None:
    plan = _plan(_command_stage("one"), _command_stage("two"), _command_stage("three"))

    assert selected_stage_numbers(plan, RunOptions(tmp_path, start_stage=2)) == (2, 3)
    assert selected_stage_numbers(plan, RunOptions(tmp_path, stage_range="2:3")) == (2, 3)
    with pytest.raises(ValueError):
        selected_stage_numbers(plan, RunOptions(tmp_path, start_stage=2, stage_range="2:3"))


def test_plan_checkpoint_resumes_without_rerunning_passed_stage(tmp_path: Path) -> None:
    plan = _plan(_command_stage("one"))
    options = RunOptions(tmp_path, heartbeat_seconds=0)

    assert run_test_plan(plan, options) == 0
    history_path = tmp_path / "duration_history.jsonl"
    first_history = history_path.read_text(encoding="utf-8").splitlines()

    assert run_test_plan(plan, RunOptions(tmp_path, resume=True, heartbeat_seconds=0)) == 0
    assert history_path.read_text(encoding="utf-8").splitlines() == first_history
    checkpoint = load_checkpoint(tmp_path, plan.name)
    assert checkpoint is not None
    assert checkpoint["stages"]["one"]["status"] == "PASS"


def test_running_checkpoint_stage_is_retried_on_resume(tmp_path: Path) -> None:
    stage = _command_stage("one", "recovered")
    plan = _plan(stage)
    checkpoint = new_checkpoint(plan)
    save_checkpoint(tmp_path, checkpoint)
    mark_stage_running(tmp_path, checkpoint, stage, log_path=stage_log_path(tmp_path, plan.name, stage))

    assert run_test_plan(plan, RunOptions(tmp_path, resume=True, heartbeat_seconds=0)) == 0
    recovered = load_checkpoint(tmp_path, plan.name)
    assert recovered is not None
    assert recovered["stages"][stage.stage_id]["status"] == "PASS"



def test_workspace_fingerprint_invalidates_resume_after_source_change(tmp_path: Path) -> None:
    stage = _command_stage("one")
    first = TestPlanSpec("unit-plan", "test plan", (stage,), workspace_fingerprint="before")
    second = TestPlanSpec("unit-plan", "test plan", (stage,), workspace_fingerprint="after")
    assert run_test_plan(first, RunOptions(tmp_path, heartbeat_seconds=0)) == 0

    with pytest.raises(ValueError, match="manifest changed"):
        run_test_plan(second, RunOptions(tmp_path, resume=True, heartbeat_seconds=0))

def test_resume_rejects_changed_manifest(tmp_path: Path) -> None:
    first = _plan(_command_stage("one", "first"))
    second = _plan(_command_stage("one", "second"))
    assert run_test_plan(first, RunOptions(tmp_path, heartbeat_seconds=0)) == 0

    with pytest.raises(ValueError, match="manifest changed"):
        run_test_plan(second, RunOptions(tmp_path, resume=True, heartbeat_seconds=0))


def test_streaming_process_writes_combined_stage_log(tmp_path: Path) -> None:
    log = tmp_path / "stage.log"
    result = run_controlled_process(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
        timeout_seconds=5,
        log_path=log,
        heartbeat_seconds=0,
        heartbeat_label="unit",
    )

    assert result.return_code == 0
    assert set(log.read_text(encoding="utf-8").splitlines()) == {"out", "err"}


def test_timeout_is_recorded_honestly_in_summary(tmp_path: Path) -> None:
    stage = TestStageSpec(
        stage_id="timeout",
        label="timeout",
        command=(sys.executable, "-c", "import time; time.sleep(30)"),
        timeout_seconds=1,
        kind="command",
    )
    plan = _plan(stage)

    assert run_test_plan(plan, RunOptions(tmp_path, heartbeat_seconds=0)) == 1
    summary = json.loads((tmp_path / plan.name / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["TIMEOUT"] == 1
    assert summary["counts"]["PASS"] == 0
