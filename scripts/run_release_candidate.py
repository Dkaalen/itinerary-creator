"""Run a strong timeout-safe release candidate validation path."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, command: tuple[str, ...]) -> int:
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(command), flush=True)
    started = time.monotonic()
    result = subprocess.run(command, cwd=REPO_ROOT, stdin=subprocess.DEVNULL)
    elapsed = time.monotonic() - started
    status = "passed" if result.returncode == 0 else f"failed ({result.returncode})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run release candidate validation.")
    parser.add_argument(
        "--include-slow",
        action="store_true",
        help="Also run the isolated slow harness after the release lane.",
    )
    args = parser.parse_args(argv)

    commands: list[tuple[str, tuple[str, ...]]] = [
        ("health check", (sys.executable, "scripts/run_health_check.py")),
        ("release groups", (sys.executable, "scripts/run_test_group.py", "release")),
    ]
    if args.include_slow:
        commands.append(("isolated slow tests", (sys.executable, "scripts/run_test_group.py", "slow")))

    for label, command in commands:
        code = _run(label, command)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
