"""Subprocess execution helpers for scripts.run_test_group."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from scripts.test_runner_models import StageRunResult
from scripts.subprocess_control import run_controlled_process

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYTEST_FLAGS = ("-q", "--durations=10")
DEFAULT_STAGE_TIMEOUT_SECONDS = int(
    os.environ.get("ITINERARY_TEST_STAGE_TIMEOUT_SECONDS", "300")
)


def _pytest_command(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> list[str]:
    stage_flags = ("-s",) if stage_name.startswith("slow ") else ()
    return [
        sys.executable,
        "scripts/run_pytest_stage.py",
        "--timeout-seconds",
        str(DEFAULT_STAGE_TIMEOUT_SECONDS),
        "--label",
        stage_name,
        "--",
        *DEFAULT_PYTEST_FLAGS,
        *stage_flags,
        *pytest_args,
        *extra_args,
    ]


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONFAULTHANDLER", "1")
    return env


def _run_command_result(
    label: str,
    cmd: list[str],
    timeout_seconds: int = DEFAULT_STAGE_TIMEOUT_SECONDS,
    *,
    env: dict[str, str] | None = None,
) -> StageRunResult:
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(cmd), flush=True)
    print(f"stage timeout: {timeout_seconds}s", flush=True)
    started = time.monotonic()
    completed = run_controlled_process(
        cmd,
        cwd=REPO_ROOT,
        env=env or _pytest_env(),
        timeout_seconds=timeout_seconds or None,
    )
    elapsed = time.monotonic() - started
    if completed.timed_out:
        print(
            f"=== {label}: timed out after {elapsed:.1f}s "
            f"(limit {timeout_seconds}s) ===",
            flush=True,
        )
        print(
            "The timed-out stage and its descendants were terminated. Run with --plan to see "
            "the exact stage split, or increase ITINERARY_TEST_STAGE_TIMEOUT_SECONDS "
            "for slower machines.",
            flush=True,
        )
        return StageRunResult(label=label, return_code=124, elapsed_seconds=elapsed)

    return_code = completed.return_code
    status = "passed" if return_code == 0 else f"failed ({return_code})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return StageRunResult(label=label, return_code=return_code, elapsed_seconds=elapsed)


def _run_command(label: str, cmd: list[str], timeout_seconds: int = DEFAULT_STAGE_TIMEOUT_SECONDS) -> int:
    """Compatibility wrapper returning only the process code."""

    return _run_command_result(label, cmd, timeout_seconds).return_code


def _run_slow_harness() -> int:
    return _run_command("slow direct harness", [sys.executable, "scripts/run_slow_tests.py"])


def _run_pytest(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> int:
    return _run_command(stage_name, _pytest_command(stage_name, pytest_args, extra_args))


def _run_pytest_result(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> StageRunResult:
    return _run_command_result(stage_name, _pytest_command(stage_name, pytest_args, extra_args))


def _child_runner_command(group_name: str, stage_number: int, extra_args: list[str]) -> list[str]:
    """Return a fresh runner command for one stage."""

    cmd = [sys.executable, str(Path(__file__).with_name("run_test_group.py")), group_name, "--stage-range", str(stage_number)]
    if extra_args:
        cmd.extend(["--", *extra_args])
    return cmd


def _print_stage_summary(results: list[StageRunResult]) -> None:
    """Print a compact summary so wrapper timeouts are easy to diagnose."""

    if not results:
        return
    total = sum(result.elapsed_seconds for result in results)
    print("\n=== Stage summary ===", flush=True)
    for result in results:
        if result.timed_out:
            status = "TIMEOUT"
        elif result.passed:
            status = "PASS"
        else:
            status = f"FAIL({result.return_code})"
        print(f"{status:>9} {result.elapsed_seconds:7.1f}s  {result.label}", flush=True)
    print(f"Total stage runtime: {total:.1f}s", flush=True)
