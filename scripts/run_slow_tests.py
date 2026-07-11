"""Run slow quality checks with simple subprocess isolation.

The slow lane exercises large real fixtures and rendered PDFs. Each direct
no-fixture target runs in its own worker process with an honest per-target
timeout. The launcher does not exec-chain itself, so a completed slow lane
returns control to CI and local runners cleanly.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_groups import slow_direct_targets
from scripts.subprocess_control import run_controlled_process

WORKER = "scripts/run_test_function_direct.py"
TEST_TIMEOUT_SECONDS = int(os.environ.get("ITINERARY_SLOW_TEST_TIMEOUT_SECONDS", "120"))


@dataclass(frozen=True)
class SlowResult:
    target: str
    exit_code: int
    elapsed_seconds: float

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def _slow_targets(repo_root: Path = REPO_ROOT) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for target in slow_direct_targets(repo_root):
        relative_path, separator, test_name = target.partition("::")
        if not separator or not test_name:
            raise ValueError(f"Slow target must be a direct test function: {target}")
        targets.append((relative_path, test_name))
    return targets


def _worker_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def _run_worker(relative_path: str, test_name: str) -> SlowResult:
    label = f"{relative_path}::{test_name}"
    args = [sys.executable, WORKER, relative_path, test_name]
    started = time.monotonic()
    result = run_controlled_process(
        args,
        cwd=REPO_ROOT,
        env=_worker_env(),
        timeout_seconds=TEST_TIMEOUT_SECONDS,
    )
    exit_code = result.return_code
    elapsed = time.monotonic() - started
    return SlowResult(label, exit_code, elapsed)


def _print_plan(targets: list[tuple[str, str]]) -> None:
    print(f"Slow isolated plan: {len(targets)} target{'s' if len(targets) != 1 else ''}", flush=True)
    for index, (relative_path, test_name) in enumerate(targets, start=1):
        print(f"  {index:02d}. {relative_path}::{test_name}", flush=True)


def _print_summary(results: list[SlowResult], started: float) -> None:
    elapsed = time.monotonic() - started
    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    print("\nSlow isolated summary", flush=True)
    print("=====================", flush=True)
    for result in results:
        status = "PASS" if result.passed else f"FAIL({result.exit_code})"
        print(f"{status:9} {result.elapsed_seconds:6.1f}s  {result.target}", flush=True)
    print(f"{passed}/{len(results)} slow targets passed in {elapsed:.1f}s", flush=True)
    if failed:
        print(f"{failed} slow target{'s' if failed != 1 else ''} failed.", flush=True)


def run_slow_targets(*, fail_fast: bool = True) -> int:
    targets = _slow_targets()
    if not targets:
        print("No slow tests discovered.", flush=True)
        return 0

    started = time.monotonic()
    results: list[SlowResult] = []
    print(f"Running {len(targets)} isolated slow targets", flush=True)
    for index, (relative_path, test_name) in enumerate(targets, start=1):
        label = f"{relative_path}::{test_name}"
        print(f"\nRUN {index}/{len(targets)} {label}", flush=True)
        result = _run_worker(relative_path, test_name)
        results.append(result)
        if result.exit_code == 124:
            print(f"TIMEOUT {label} after {TEST_TIMEOUT_SECONDS}s", flush=True)
        elif result.passed:
            print(f"PASS {index}/{len(targets)} {label} in {result.elapsed_seconds:.1f}s", flush=True)
        else:
            print(f"FAIL {index}/{len(targets)} {label} exited with {result.exit_code}", flush=True)
        if not result.passed and fail_fast:
            _print_summary(results, started)
            return result.exit_code

    _print_summary(results, started)
    return 0 if all(result.passed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated slow itinerary tests.")
    parser.add_argument("--plan", action="store_true", help="Show slow targets without running them.")
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue running slow targets after a failure and report a combined summary.",
    )
    args = parser.parse_args(argv)
    targets = _slow_targets()
    if args.plan:
        _print_plan(targets)
        return 0
    return run_slow_targets(fail_fast=not args.no_fail_fast)


if __name__ == "__main__":
    raise SystemExit(main())
