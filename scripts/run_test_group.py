"""Run named pytest groups with readable progress output."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_groups import GROUPS, build_full_stages, missing_group_paths

DEFAULT_PYTEST_FLAGS = ("-q", "--durations=10")
DEFAULT_STAGE_TIMEOUT_SECONDS = int(
    os.environ.get("ITINERARY_TEST_STAGE_TIMEOUT_SECONDS", "300")
)


def _split_extra_pytest_args(extra_args: list[str]) -> list[str]:
    if extra_args and extra_args[0] == "--":
        return extra_args[1:]
    return extra_args


def _run_pytest(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> int:
    cmd = [sys.executable, "-m", "pytest", *DEFAULT_PYTEST_FLAGS, *pytest_args, *extra_args]
    print(f"\n=== {stage_name} ===", flush=True)
    print(" ".join(cmd), flush=True)
    started = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            timeout=DEFAULT_STAGE_TIMEOUT_SECONDS or None,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        print(
            f"=== {stage_name}: timed out after {elapsed:.1f}s "
            f"(limit {DEFAULT_STAGE_TIMEOUT_SECONDS}s) ===",
            flush=True,
        )
        print(
            "Increase ITINERARY_TEST_STAGE_TIMEOUT_SECONDS if you are running "
            "this locally and want to allow longer stages.",
            flush=True,
        )
        return 124

    elapsed = time.monotonic() - started
    status = "passed" if result.returncode == 0 else f"failed ({result.returncode})"
    print(f"=== {stage_name}: {status} in {elapsed:.1f}s ===", flush=True)
    return result.returncode


def run_named_group(group_name: str, extra_args: list[str]) -> int:
    missing = missing_group_paths(REPO_ROOT)
    if missing:
        print("Configured test group paths are missing:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    if group_name == "full":
        stages = build_full_stages(REPO_ROOT)
    else:
        stages = ((group_name, GROUPS[group_name]),)

    if group_name == "full":
        print(f"Full suite plan: {len(stages)} progress-tracked stages", flush=True)

    for stage_name, pytest_paths in stages:
        code = _run_pytest(stage_name, tuple(pytest_paths), extra_args)
        if code != 0:
            return code
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Itinerary App pytest groups with progress by suite bucket."
    )
    parser.add_argument(
        "group",
        choices=("fast", "quality", "pdf", "slow", "full"),
        help="Named test group to run.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Optional extra pytest args. Use -- before pytest flags, e.g. -- -k parser.",
    )
    args = parser.parse_args(argv)
    return run_named_group(args.group, _split_extra_pytest_args(args.pytest_args))


if __name__ == "__main__":
    raise SystemExit(main())
