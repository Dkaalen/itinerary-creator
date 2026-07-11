"""Public CLI for resumable Itinerary App validation plans."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_runner_manifest import AVAILABLE_PLAN_NAMES, build_test_plan
from scripts.test_runner_orchestrator import RunOptions, print_test_plan, run_test_plan
from scripts.test_runner_state import DEFAULT_STATE_ROOT_NAME


def _split_passthrough(argv: list[str]) -> tuple[list[str], tuple[str, ...]]:
    if "--" not in argv:
        return argv, ()
    index = argv.index("--")
    return argv[:index], tuple(argv[index + 1 :])


def main(argv: list[str] | None = None) -> int:
    runner_args, pytest_args = _split_passthrough(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(description="Run a resumable staged test plan.")
    parser.add_argument("--plan", choices=AVAILABLE_PLAN_NAMES, help="Plan to execute.")
    parser.add_argument("--list-plans", action="store_true")
    parser.add_argument("--show-plan", action="store_true", help="Print the manifest without running it.")
    parser.add_argument("--resume", action="store_true", help="Skip checkpointed PASS stages.")
    parser.add_argument("--reset", action="store_true", help="Discard the current plan checkpoint first.")
    parser.add_argument("--start-stage", type=int, help="Run from this one-based stage number onward.")
    parser.add_argument("--stage-range", default="", help="Run a one-based inclusive range, e.g. 10:25.")
    parser.add_argument("--no-fail-fast", action="store_true", help="Continue after failed stages.")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_ROOT_NAME)
    parser.add_argument("--heartbeat-seconds", type=float, default=20.0)
    args = parser.parse_args(runner_args)

    if args.list_plans:
        for name in AVAILABLE_PLAN_NAMES:
            print(name)
        return 0
    if not args.plan:
        parser.error("--plan is required unless --list-plans is used")

    plan = build_test_plan(args.plan, extra_pytest_args=pytest_args)
    if args.show_plan:
        print_test_plan(plan)
        return 0

    options = RunOptions(
        state_root=(ROOT / args.state_dir).resolve(),
        resume=args.resume,
        reset=args.reset,
        start_stage=args.start_stage,
        stage_range=args.stage_range or None,
        fail_fast=not args.no_fail_fast,
        heartbeat_seconds=max(0.0, args.heartbeat_seconds),
    )
    try:
        return run_test_plan(plan, options)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
