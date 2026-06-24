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

from scripts.test_groups import (
    GROUPS,
    GROUP_ORDER,
    CHUNKED_GROUP_STAGE_SIZES,
    chunked_group_stages,
    build_full_stages,
    build_slow_stages,
    group_descriptions,
    missing_group_paths,
)

DEFAULT_PYTEST_FLAGS = ("-q", "--durations=10")
DEFAULT_STAGE_TIMEOUT_SECONDS = int(
    os.environ.get("ITINERARY_TEST_STAGE_TIMEOUT_SECONDS", "300")
)
RUNNER_GROUPS = (*GROUP_ORDER, "full")


def _split_extra_pytest_args(extra_args: list[str]) -> list[str]:
    if extra_args and extra_args[0] == "--":
        return extra_args[1:]
    return extra_args


def _pytest_command(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> list[str]:
    stage_flags = ("-s",) if stage_name.startswith("slow ") else ()
    return [sys.executable, "-m", "pytest", *DEFAULT_PYTEST_FLAGS, *stage_flags, *pytest_args, *extra_args]


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    return env


def _run_slow_harness() -> int:
    cmd = [sys.executable, "scripts/run_slow_tests.py"]
    print("\n=== slow direct harness ===", flush=True)
    print(" ".join(cmd), flush=True)
    started = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=_pytest_env(),
            stdin=subprocess.DEVNULL,
            timeout=DEFAULT_STAGE_TIMEOUT_SECONDS or None,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        print(
            f"=== slow direct harness: timed out after {elapsed:.1f}s "
            f"(limit {DEFAULT_STAGE_TIMEOUT_SECONDS}s) ===",
            flush=True,
        )
        return 124

    elapsed = time.monotonic() - started
    status = "passed" if result.returncode == 0 else f"failed ({result.returncode})"
    print(f"=== slow direct harness: {status} in {elapsed:.1f}s ===", flush=True)
    return result.returncode


def _run_pytest(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> int:
    cmd = _pytest_command(stage_name, pytest_args, extra_args)
    print(f"\n=== {stage_name} ===", flush=True)
    print(" ".join(cmd), flush=True)
    started = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=_pytest_env(),
            stdin=subprocess.DEVNULL,
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


def _stages_for_group(group_name: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if group_name == "full":
        return build_full_stages(REPO_ROOT)
    if group_name == "slow":
        return build_slow_stages()
    if group_name in {"fast", "quality", *CHUNKED_GROUP_STAGE_SIZES}:
        return chunked_group_stages(
            group_name,
            GROUPS[group_name],
            stage_size=CHUNKED_GROUP_STAGE_SIZES.get(group_name, 4),
        )
    return ((group_name, GROUPS[group_name]),)


def _print_group_plan(group_name: str) -> None:
    descriptions = group_descriptions()
    stages = _stages_for_group(group_name)
    print(f"{group_name}: {descriptions.get(group_name, 'progress-tracked full validation')}")
    print(f"Stages: {len(stages)}")
    for index, (stage_name, pytest_paths) in enumerate(stages, start=1):
        print(f"  {index:02d}. {stage_name} ({len(pytest_paths)} target{'s' if len(pytest_paths) != 1 else ''})")
        for path in pytest_paths:
            print(f"      - {path}")


def _print_available_groups() -> None:
    descriptions = group_descriptions()
    print("Available test groups:")
    for name in RUNNER_GROUPS:
        description = descriptions.get(name, "progress-tracked full validation")
        print(f"  {name:12} {description}")


def run_named_group(group_name: str, extra_args: list[str]) -> int:
    missing = missing_group_paths(REPO_ROOT)
    if missing:
        print("Configured test group paths are missing:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    if group_name == "slow" and not extra_args:
        return _run_slow_harness()

    stages = _stages_for_group(group_name)

    if group_name == "full":
        print(f"Full suite plan: {len(stages)} progress-tracked stages", flush=True)

    for stage_name, pytest_paths in stages:
        code = _run_pytest(stage_name, tuple(pytest_paths), extra_args)
        if code != 0:
            return code
    return 0


def _extract_runner_flags(argv: list[str]) -> tuple[list[str], bool, bool]:
    """Pull runner flags out before pytest passthrough args consume them."""

    if "--" in argv:
        separator_index = argv.index("--")
        runner_side = argv[:separator_index]
        pytest_side = argv[separator_index:]
    else:
        runner_side = argv
        pytest_side = []

    list_groups = "--list-groups" in runner_side
    plan = "--plan" in runner_side
    remaining = [arg for arg in runner_side if arg not in {"--list-groups", "--plan"}]
    return [*remaining, *pytest_side], list_groups, plan


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
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
    args = parser.parse_args(runner_args)

    if list_groups:
        _print_available_groups()
        return 0

    if not args.group:
        parser.error("the following arguments are required: group unless --list-groups is used")

    if plan:
        _print_group_plan(args.group)
        return 0

    return run_named_group(args.group, _split_extra_pytest_args(args.pytest_args))


if __name__ == "__main__":
    raise SystemExit(main())
