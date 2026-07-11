"""Resumable stage orchestration for all repository validation plans."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import time

from scripts.subprocess_control import run_controlled_process
from scripts.test_runner_args import _parse_stage_range
from scripts.test_runner_models import StageRunResult, TestPlanSpec, TestStageSpec
from scripts.test_runner_state import (
    build_summary,
    completed_stage_ids,
    load_checkpoint,
    mark_stage_running,
    new_checkpoint,
    plan_state_dir,
    prior_duration_median,
    record_stage_result,
    save_checkpoint,
    stage_log_path,
    utc_now,
    validate_checkpoint,
    write_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEARTBEAT_SECONDS = float(os.environ.get("ITINERARY_TEST_HEARTBEAT_SECONDS", "20"))


@dataclass(frozen=True)
class RunOptions:
    state_root: Path
    resume: bool = False
    reset: bool = False
    start_stage: int | None = None
    stage_range: str | None = None
    fail_fast: bool = True
    heartbeat_seconds: float = DEFAULT_HEARTBEAT_SECONDS


def _runner_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONFAULTHANDLER", "1")
    return env


def selected_stage_numbers(plan: TestPlanSpec, options: RunOptions) -> tuple[int, ...]:
    if options.start_stage is not None and options.stage_range:
        raise ValueError("Use either --start-stage or --stage-range, not both.")
    if options.start_stage is not None:
        if options.start_stage < 1 or options.start_stage > len(plan.stages):
            raise ValueError(f"Invalid --start-stage; use 1:{len(plan.stages)}.")
        return tuple(range(options.start_stage, len(plan.stages) + 1))
    stage_slice = _parse_stage_range(options.stage_range, len(plan.stages))
    return tuple(range(1, len(plan.stages) + 1))[stage_slice]


def _duration_regression(stage: TestStageSpec, elapsed: float, prior_median: float | None) -> str:
    if prior_median is None or prior_median <= 0 or elapsed < 10:
        return ""
    ratio = elapsed / prior_median
    if ratio < 2.0 or elapsed - prior_median < 10:
        return ""
    return (
        f"DURATION REGRESSION: {stage.label} took {elapsed:.1f}s; "
        f"prior median {prior_median:.1f}s ({ratio:.1f}x)."
    )


def _print_summary(summary: dict[str, object], summary_file: Path) -> None:
    counts = summary["counts"]
    assert isinstance(counts, dict)
    print("\n=== Test plan summary ===", flush=True)
    for row in summary["stages"]:
        assert isinstance(row, dict)
        elapsed = row.get("elapsed_seconds")
        elapsed_text = f"{float(elapsed):7.1f}s" if isinstance(elapsed, (int, float)) else "       -"
        print(
            f"{str(row['status']):>9} {elapsed_text}  "
            f"{int(row['number']):03d}. {row['label']}",
            flush=True,
        )
    print(
        "Counts: "
        f"PASS {counts.get('PASS', 0)} · FAIL {counts.get('FAIL', 0)} · "
        f"TIMEOUT {counts.get('TIMEOUT', 0)} · NOT RUN {counts.get('NOT_RUN', 0)} · "
        f"RUNNING {counts.get('RUNNING', 0)}",
        flush=True,
    )
    print(f"Checkpoint summary: {summary_file}", flush=True)


def _checkpoint_for_run(plan: TestPlanSpec, options: RunOptions) -> dict[str, object]:
    state_dir = plan_state_dir(options.state_root, plan.name)
    if options.reset and state_dir.exists():
        shutil.rmtree(state_dir)

    existing = load_checkpoint(options.state_root, plan.name)
    if options.resume and existing is not None:
        valid, reason = validate_checkpoint(plan, existing)
        if not valid:
            raise ValueError(
                f"Cannot resume {plan.name}: {reason}. Run again with --reset to start fresh."
            )
        return existing

    checkpoint = new_checkpoint(plan)
    save_checkpoint(options.state_root, checkpoint)
    return checkpoint


def run_test_plan(plan: TestPlanSpec, options: RunOptions) -> int:
    """Run selected stages, persisting state after every transition."""

    selected_numbers = selected_stage_numbers(plan, options)
    selected_ids = {plan.stages[number - 1].stage_id for number in selected_numbers}
    checkpoint = _checkpoint_for_run(plan, options)
    completed = completed_stage_ids(checkpoint) if options.resume else set()

    print(f"Test plan: {plan.name} — {plan.description}", flush=True)
    print(f"Manifest fingerprint: {plan.fingerprint[:12]}", flush=True)
    print(f"Workspace fingerprint: {plan.workspace_fingerprint[:12]}", flush=True)
    print(f"Selected stages: {len(selected_numbers)} of {len(plan.stages)}", flush=True)
    print(f"State directory: {plan_state_dir(options.state_root, plan.name)}", flush=True)

    selected_failed = False
    for stage_number in selected_numbers:
        stage = plan.stages[stage_number - 1]
        if stage.stage_id in completed:
            print(f"\nSKIP {stage_number}/{len(plan.stages)} {stage.label} (checkpoint PASS)", flush=True)
            continue

        log_path = stage_log_path(options.state_root, plan.name, stage)
        prior_median = prior_duration_median(options.state_root, stage)
        started_at = mark_stage_running(
            options.state_root,
            checkpoint,
            stage,
            log_path=log_path,
        )
        print(f"\nRUN {stage_number}/{len(plan.stages)} {stage.label}", flush=True)
        print(" ".join(stage.command), flush=True)
        print(f"Timeout: {stage.timeout_seconds}s · Log: {log_path}", flush=True)

        started = time.monotonic()
        completed_process = run_controlled_process(
            stage.command,
            cwd=REPO_ROOT,
            env=_runner_env(),
            timeout_seconds=stage.timeout_seconds,
            log_path=log_path,
            heartbeat_seconds=options.heartbeat_seconds,
            heartbeat_label=f"stage {stage_number}/{len(plan.stages)} {stage.label}",
        )
        elapsed = time.monotonic() - started
        result = StageRunResult(
            label=stage.label,
            return_code=completed_process.return_code,
            elapsed_seconds=elapsed,
            stage_id=stage.stage_id,
            log_path=str(log_path),
            started_at=started_at,
            finished_at=utc_now(),
            prior_median_seconds=prior_median,
        )
        record_stage_result(options.state_root, checkpoint, stage, result)
        print(f"{result.status} {stage.label} in {elapsed:.1f}s", flush=True)
        warning = _duration_regression(stage, elapsed, prior_median)
        if warning:
            print(warning, flush=True)

        if not result.passed:
            selected_failed = True
            if options.fail_fast:
                break

    summary = build_summary(plan, checkpoint, selected_ids)
    summary_file = write_summary(options.state_root, plan, summary)
    _print_summary(summary, summary_file)

    selected_rows = [
        row
        for row in summary["stages"]
        if isinstance(row, dict) and row.get("stage_id") in selected_ids
    ]
    all_selected_passed = bool(selected_rows) and all(row.get("status") == "PASS" for row in selected_rows)
    return 0 if all_selected_passed and not selected_failed else 1


def print_test_plan(plan: TestPlanSpec) -> None:
    print(f"{plan.name}: {plan.description}")
    print(f"Manifest fingerprint: {plan.fingerprint}")
    print(f"Workspace fingerprint: {plan.workspace_fingerprint}")
    print(f"Stages: {len(plan.stages)}")
    for index, stage in enumerate(plan.stages, start=1):
        print(
            f"  {index:03d}. {stage.label} "
            f"[{stage.kind}, timeout {stage.timeout_seconds}s, id {stage.stage_id}]"
        )
        for target in stage.targets:
            print(f"       - {target}")
