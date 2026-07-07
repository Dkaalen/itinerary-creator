"""Run the instant local health check for everyday patch work.

This command is intentionally small.  It proves the app imports, core Python
files compile, architecture guards still load, and the critical product-surface
smoke lane passes.  Slower collection/audit/release lanes belong to
``run_release_candidate.py``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("compile", (sys.executable, "-m", "compileall", "-q", ".")),
    ("import smoke", (sys.executable, "scripts/import_smoke.py")),
    ("architecture guards", (sys.executable, "scripts/architecture_guards.py")),
    ("critical product smoke", (sys.executable, "scripts/run_test_group.py", "critical")),
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


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    return env


def _run(label: str, command: tuple[str, ...]) -> int:
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(command), flush=True)
    started = time.monotonic()
    result = subprocess.run(command, cwd=REPO_ROOT, env=_env(), stdin=subprocess.DEVNULL)
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
