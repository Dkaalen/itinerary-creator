"""Run strong timeout-safe release candidate validation.

The release command is broader than the instant health check but still avoids raw
full pytest. Every external step has an honest timeout so the command fails with
a useful message instead of hanging silently.
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEP_TIMEOUT_SECONDS = int(
    os.environ.get("ITINERARY_RELEASE_STEP_TIMEOUT_SECONDS", "900")
)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def _run(label: str, command: tuple[str, ...], *, timeout_seconds: int = DEFAULT_STEP_TIMEOUT_SECONDS) -> int:
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(command), flush=True)
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=_env(),
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds or None,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        print(
            f"=== {label}: timed out after {elapsed:.1f}s "
            f"(limit {timeout_seconds}s) ===",
            flush=True,
        )
        return 124

    elapsed = time.monotonic() - started
    status = "passed" if exit_code == 0 else f"failed ({exit_code})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return exit_code


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
    parser.add_argument(
        "--include-slow",
        action="store_true",
        help="Also run the isolated slow harness after the release lane.",
    )
    parser.add_argument(
        "--skip-node",
        action="store_true",
        help="Skip frontend JavaScript syntax checks when Node.js is unavailable.",
    )
    args = parser.parse_args(argv)

    commands: list[tuple[str, tuple[str, ...]]] = [
        ("instant health check", (sys.executable, "scripts/run_health_check.py")),
        ("pytest collect-only", (sys.executable, "-m", "pytest", "--collect-only", "-q")),
        ("test-suite audit", (sys.executable, "scripts/test_suite_audit.py")),
        ("release groups", (sys.executable, "scripts/run_test_group.py", "release")),
    ]
    if args.include_slow:
        commands.append(("isolated slow tests", (sys.executable, "scripts/run_test_group.py", "slow")))
    if not args.skip_node:
        commands.extend(_node_check_commands())
    commands.append(("diff whitespace check", ("git", "--no-pager", "diff", "--check")))

    for label, command in commands:
        code = _run(label, command)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
