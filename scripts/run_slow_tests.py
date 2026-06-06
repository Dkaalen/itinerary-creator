"""Run slow quality checks with process-chain isolation.

The slow lane exercises large real fixtures and rendered PDFs. A single pytest
session can hang when renderer/PDF globals and pytest teardown interact. A
long-lived Python launcher can also become unreliable after repeatedly spawning
heavy render tests in constrained environments. This runner therefore restarts
itself between slow targets: each launcher process runs one no-fixture test in a
fresh worker, then ``exec``-replaces itself with the next launcher.
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_groups import SLOW_TESTS

WORKER = "scripts/run_test_function_direct.py"
TEST_TIMEOUT_SECONDS = int(os.environ.get("ITINERARY_SLOW_TEST_TIMEOUT_SECONDS", "120"))
STARTED_ENV = "ITINERARY_SLOW_CHAIN_STARTED"


def _test_names(relative_path: str) -> list[str]:
    tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        and not node.args.args
    ]


def _slow_targets() -> list[tuple[str, str]]:
    return [
        (relative_path, test_name)
        for relative_path in SLOW_TESTS
        for test_name in _test_names(relative_path)
    ]


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
