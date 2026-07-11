"""Run the compact release proof through the shared resumable manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_runner_manifest import PROOF_PLAN_NAME, build_test_plan
from scripts.test_runner_orchestrator import RunOptions, print_test_plan, run_test_plan
from scripts.test_runner_state import DEFAULT_STATE_ROOT_NAME


def build_plan() -> list[dict[str, object]]:
    """Return the public proof plan shape used by regression tests and reports."""

    plan = build_test_plan(PROOF_PLAN_NAME)
    return [
        {
            "stage_id": stage.stage_id,
            "label": stage.label,
            "command": list(stage.command),
            "timeout_seconds": stage.timeout_seconds,
            "kind": stage.kind,
        }
        for stage in plan.stages
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the compact resumable validation proof.")
    parser.add_argument("--plan", action="store_true", help="Print the proof manifest without executing it.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--start-stage", type=int)
    parser.add_argument("--stage-range", default="")
    parser.add_argument("--no-fail-fast", action="store_true")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_ROOT_NAME)
    parser.add_argument("--heartbeat-seconds", type=float, default=20.0)
    parser.add_argument(
        "--include-group-tour",
        action="store_true",
        help="Compatibility flag; group-tour ownership is already part of the proof manifest.",
    )
    args = parser.parse_args(argv)

    plan = build_test_plan(PROOF_PLAN_NAME)
    if args.plan:
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
