"""Compatibility CLI for named pytest groups.

The executable manifest and resume logic live in ``run_test_plan.py``. This
wrapper preserves the established positional group commands used by PowerShell
and CI while delegating execution to the same orchestrator.
"""

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
from scripts.test_runner_execution import _pytest_command, _pytest_env
from scripts.test_runner_manifest import build_test_plan
from scripts.test_runner_orchestrator import RunOptions, print_test_plan, run_test_plan
from scripts.test_runner_plans import RUNNER_GROUPS, _print_available_groups, _stages_for_group
from scripts.test_runner_state import DEFAULT_STATE_ROOT_NAME


def run_named_group(
    group_name: str,
    extra_args: list[str],
    *,
    stage_range: str | None = None,
    resume: bool = False,
    reset: bool = False,
    start_stage: int | None = None,
    fail_fast: bool = True,
    state_dir: str = DEFAULT_STATE_ROOT_NAME,
    heartbeat_seconds: float = 20.0,
) -> int:
    missing = missing_group_paths(REPO_ROOT)
    if missing:
        print("Configured test group paths are missing:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    plan = build_test_plan(group_name, extra_pytest_args=tuple(extra_args))
    options = RunOptions(
        state_root=(REPO_ROOT / state_dir).resolve(),
        resume=resume,
        reset=reset,
        start_stage=start_stage,
        stage_range=stage_range,
        fail_fast=fail_fast,
        heartbeat_seconds=max(0.0, heartbeat_seconds),
    )
    try:
        return run_test_plan(plan, options)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2


def _split_cli(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def main(argv: list[str] | None = None) -> int:
    runner_args, pytest_args = _split_cli(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(
        description="Run Itinerary App pytest groups with resumable progress."
    )
    parser.add_argument("group", nargs="?", choices=RUNNER_GROUPS)
    parser.add_argument("--list-groups", action="store_true")
    parser.add_argument("--plan", action="store_true", help="Show the selected plan without running it.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--start-stage", type=int)
    parser.add_argument("--stage-range", default="")
    parser.add_argument("--no-fail-fast", action="store_true")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_ROOT_NAME)
    parser.add_argument("--heartbeat-seconds", type=float, default=20.0)
    args = parser.parse_args(runner_args)

    if args.list_groups:
        _print_available_groups()
        return 0
    if not args.group:
        parser.error("a group is required unless --list-groups is used")

    plan = build_test_plan(args.group, extra_pytest_args=tuple(pytest_args))
    if args.plan:
        print_test_plan(plan)
        return 0

    return run_named_group(
        args.group,
        pytest_args,
        stage_range=args.stage_range or None,
        resume=args.resume,
        reset=args.reset,
        start_stage=args.start_stage,
        fail_fast=not args.no_fail_fast,
        state_dir=args.state_dir,
        heartbeat_seconds=args.heartbeat_seconds,
    )


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
