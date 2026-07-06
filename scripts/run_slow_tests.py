"""Run slow quality checks with process-chain isolation.

The slow lane exercises large real fixtures and rendered PDFs. Each direct
no-fixture test target is executed in a fresh worker process, then the launcher
``exec``-replaces itself with the next target. This keeps renderer/PDF globals
from leaking across slow checks and makes timeouts fail honestly.
"""

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

from scripts.test_groups import slow_direct_targets

WORKER = "scripts/run_test_function_direct.py"
TEST_TIMEOUT_SECONDS = int(os.environ.get("ITINERARY_SLOW_TEST_TIMEOUT_SECONDS", "120"))
STARTED_ENV = "ITINERARY_SLOW_CHAIN_STARTED"


def _slow_targets() -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for target in slow_direct_targets(REPO_ROOT):
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


def _run_worker(relative_path: str, test_name: str) -> int:
    args = [sys.executable, WORKER, relative_path, test_name]
    try:
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            env=_worker_env(),
            stdin=subprocess.DEVNULL,
            timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(
            f"TIMEOUT {relative_path}::{test_name} after {TEST_TIMEOUT_SECONDS}s",
            flush=True,
        )
        return 124
    return result.returncode


def _exec_next(index: int) -> None:
    env = _worker_env()
    env.setdefault(STARTED_ENV, str(time.monotonic()))
    os.execvpe(
        sys.executable,
        [sys.executable, "scripts/run_slow_tests.py", "--chain-index", str(index)],
        env,
    )


def _run_chain(index: int) -> int:
    targets = _slow_targets()
    if not targets:
        print("No slow tests discovered.", flush=True)
        return 0

    if STARTED_ENV not in os.environ:
        os.environ[STARTED_ENV] = str(time.monotonic())

    if index >= len(targets):
        started = float(os.environ.get(STARTED_ENV, time.monotonic()))
        elapsed = time.monotonic() - started
        print(f"{len(targets)} slow tests passed in {elapsed:.1f}s", flush=True)
        return 0

    relative_path, test_name = targets[index]
    label = f"{relative_path}::{test_name}"
    print(f"RUN {index + 1}/{len(targets)} {label}", flush=True)
    code = _run_worker(relative_path, test_name)
    if code != 0:
        print(f"FAIL {label} exited with {code}", flush=True)
        return code

    print(f"PASS {index + 1}/{len(targets)} {label}", flush=True)
    _exec_next(index + 1)
    raise AssertionError("unreachable after exec")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated slow itinerary tests.")
    parser.add_argument("--chain-index", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return _run_chain(args.chain_index)


if __name__ == "__main__":
    raise SystemExit(main())
