"""Run the quick local health check used before focused patch validation."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("compile", (sys.executable, "-m", "compileall", "-q", ".")),
    ("import smoke", (sys.executable, "scripts/import_smoke.py")),
    ("architecture guards", (sys.executable, "scripts/architecture_guards.py")),
    ("pytest collect-only", (sys.executable, "-m", "pytest", "--collect-only", "-q")),
    ("test-suite audit", (sys.executable, "scripts/test_suite_audit.py")),
    (
        "runner guard tests",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/test_test_runner_groups.py",
            "tests/test_ci_workflow_guards.py",
            "tests/test_pytest_marker_discipline.py",
            "-q",
        ),
    ),
)


def _run(label: str, command: tuple[str, ...]) -> int:
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(command), flush=True)
    started = time.monotonic()
    result = subprocess.run(command, cwd=REPO_ROOT, stdin=subprocess.DEVNULL)
    elapsed = time.monotonic() - started
    status = "passed" if result.returncode == 0 else f"failed ({result.returncode})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return result.returncode


def main() -> int:
    for label, command in COMMANDS:
        code = _run(label, command)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
