"""Run strong, resumable release-candidate validation."""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.subprocess_control import run_controlled_process
from scripts.test_group_catalog import TEST_STAGE_BOUNDARY_SECONDS
from scripts.test_runner_manifest import build_test_plan
from scripts.test_runner_orchestrator import RunOptions, run_test_plan
from scripts.test_runner_state import DEFAULT_STATE_ROOT_NAME

DEFAULT_STEP_TIMEOUT_SECONDS = max(
    1,
    min(
        int(
            os.environ.get(
                "ITINERARY_RELEASE_STEP_TIMEOUT_SECONDS",
                str(TEST_STAGE_BOUNDARY_SECONDS),
            )
        ),
        TEST_STAGE_BOUNDARY_SECONDS,
    ),
)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONFAULTHANDLER", "1")
    return env


def _run(label: str, command: tuple[str, ...], *, timeout_seconds: int = DEFAULT_STEP_TIMEOUT_SECONDS) -> int:
    timeout_seconds = max(1, min(timeout_seconds, TEST_STAGE_BOUNDARY_SECONDS))
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(command), flush=True)
    started = time.monotonic()
    result = run_controlled_process(
        command,
        cwd=REPO_ROOT,
        env=_env(),
        timeout_seconds=timeout_seconds or None,
    )
    elapsed = time.monotonic() - started
    if result.timed_out:
        print(
            f"=== {label}: TIMEOUT after {elapsed:.1f}s "
            f"(limit {timeout_seconds}s; process tree terminated) ===",
            flush=True,
        )
        return 124
    status = "PASS" if result.return_code == 0 else f"FAIL({result.return_code})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return result.return_code


def _run_manifest_plan(plan_name: str, *, resume: bool, reset: bool) -> int:
    """Run one bounded manifest in-process so no outer timeout kills later stages."""

    print(f"\n=== {plan_name} plan ===", flush=True)
    plan = build_test_plan(plan_name)
    return run_test_plan(
        plan,
        RunOptions(
            state_root=REPO_ROOT / DEFAULT_STATE_ROOT_NAME,
            resume=resume,
            reset=reset,
        ),
    )


def _node_check_commands() -> list[tuple[str, tuple[str, ...]]]:
    commands: list[tuple[str, tuple[str, ...]]] = []
    for pattern in (
        "calculator_grid_component/frontend/js/*.js",
        "visual_editor_component/frontend/js/*.js",
    ):
        files = tuple(sorted(glob.glob(str(REPO_ROOT / pattern))))
        if files:
            commands.append((f"node syntax {pattern}", ("node", "--check", *files)))
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run release candidate validation.")
    parser.add_argument("--include-slow", action="store_true")
    parser.add_argument("--skip-node", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Resume checkpointed release/slow plans.")
    parser.add_argument("--reset", action="store_true", help="Reset release/slow checkpoints first.")
    args = parser.parse_args(argv)

    preflight_commands: list[tuple[str, tuple[str, ...]]] = [
        ("instant health check", (sys.executable, "scripts/run_health_check.py")),
        ("pytest collect-only", (sys.executable, "-m", "pytest", "--collect-only", "-q")),
        ("test-suite audit", (sys.executable, "scripts/test_suite_audit.py")),
    ]
    for label, command in preflight_commands:
        code = _run(label, command)
        if code != 0:
            return code

    code = _run_manifest_plan("release", resume=args.resume, reset=args.reset)
    if code != 0:
        return code
    if args.include_slow:
        code = _run_manifest_plan("slow", resume=args.resume, reset=args.reset)
        if code != 0:
            return code

    postflight_commands = [] if args.skip_node else _node_check_commands()
    postflight_commands.append(("diff whitespace check", ("git", "--no-pager", "diff", "--check")))
    for label, command in postflight_commands:
        code = _run(label, command)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
