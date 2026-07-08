"""Run named pytest groups with readable progress output."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_groups import missing_group_paths
from scripts.test_runner_args import (
    _extract_runner_flags,
    _parse_stage_range,
    _pull_stage_range,
    _split_extra_pytest_args,
)
from scripts.test_runner_execution import (
    DEFAULT_STAGE_TIMEOUT_SECONDS,
    _child_runner_command,
    _print_stage_summary,
    _pytest_command,
    _pytest_env,
    _run_command_result,
    _run_pytest_result,
    _run_slow_harness,
)
from scripts.test_runner_models import StageRunResult
from scripts.test_runner_plans import (
    RUNNER_GROUPS,
    _print_available_groups,
    _print_group_plan,
    _stages_for_group,
)


def run_named_group(group_name: str, extra_args: list[str], *, stage_range: str | None = None) -> int:
    missing = missing_group_paths(REPO_ROOT)
    if missing:
        print("Configured test group paths are missing:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    if group_name == "slow" and not extra_args:
        return _run_slow_harness()

    stages = _stages_for_group(group_name)
    try:
        stage_slice = _parse_stage_range(stage_range, len(stages))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    selected_stages = stages[stage_slice]
    selected_indices = list(range(1, len(stages) + 1))[stage_slice]

    if group_name in {"health", "release", "full"}:
        print(f"{group_name.title()} suite plan: {len(stages)} progress-tracked stages", flush=True)
    if stage_range:
        print(f"Running stage range {stage_range}: {len(selected_stages)} of {len(stages)} stages", flush=True)

    # Parent runner: delegate multi-stage ranges to fresh runner processes. This
    # keeps long validation lanes resilient when a render/PDF-heavy pytest
    # subprocess leaves shutdown work behind after reporting test success.
    if len(selected_stages) > 1 and not os.environ.get("ITINERARY_TEST_RUNNER_CHILD"):
        results: list[StageRunResult] = []
        for stage_number, (stage_name, _pytest_paths) in zip(selected_indices, selected_stages):
            env = _pytest_env()
            env["ITINERARY_TEST_RUNNER_CHILD"] = "1"
            result = _run_command_result(
                f"{stage_name} runner",
                _child_runner_command(group_name, stage_number, extra_args),
                timeout_seconds=DEFAULT_STAGE_TIMEOUT_SECONDS + 60,
                env=env,
            )
            results.append(result)
            if result.return_code != 0:
                _print_stage_summary(results)
                return result.return_code
        _print_stage_summary(results)
        return 0

    results: list[StageRunResult] = []
    for stage_name, pytest_paths in selected_stages:
        result = _run_pytest_result(stage_name, tuple(pytest_paths), extra_args)
        results.append(result)
        if result.return_code != 0:
            _print_stage_summary(results)
            return result.return_code
    _print_stage_summary(results)
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    pulled_stage_range, raw_args = _pull_stage_range(raw_args)
    runner_args, list_groups, plan = _extract_runner_flags(raw_args)

    parser = argparse.ArgumentParser(
        description="Run Itinerary App pytest groups with progress by suite bucket."
    )
    parser.add_argument(
        "group",
        nargs="?",
        choices=RUNNER_GROUPS,
        help="Named test group to run.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Optional extra pytest args. Use -- before pytest flags, e.g. -- -k parser.",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="Show available groups and exit without running pytest.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show the selected group's staged pytest plan without running it.",
    )
    parser.add_argument(
        "--stage-range",
        default="",
        help="Run a one-based inclusive stage range such as 1:8 or 9:17.",
    )
    args = parser.parse_args(runner_args)

    if list_groups:
        _print_available_groups()
        return 0

    if not args.group:
        parser.error("the following arguments are required: group unless --list-groups is used")

    if plan:
        _print_group_plan(args.group)
        return 0

    return run_named_group(args.group, _split_extra_pytest_args(args.pytest_args), stage_range=args.stage_range or pulled_stage_range)


if __name__ == "__main__":
    exit_code = main()
    # Pytest/render-heavy stages can leave non-daemon cleanup work behind after
    # the runner has already printed a PASS/FAIL summary.  Flush explicitly and
    # terminate the process so validation wrappers do not hang during Python
    # interpreter shutdown.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
