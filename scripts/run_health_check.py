"""Run the instant local health check for everyday patch work.

This command is intentionally small.  It proves the app imports, core Python
files compile, architecture guards still load, and the critical product-surface
smoke lane passes.  Slower collection/audit/release lanes belong to
``run_release_candidate.py``.
"""

from __future__ import annotations

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

COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("compile", (sys.executable, "-m", "compileall", "-q", ".")),
    ("import smoke", (sys.executable, "scripts/import_smoke.py")),
    ("architecture guards", (sys.executable, "scripts/architecture_guards.py")),
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
    result = run_controlled_process(
        command,
        cwd=REPO_ROOT,
        env=_env(),
        timeout_seconds=TEST_STAGE_BOUNDARY_SECONDS,
    )
    elapsed = time.monotonic() - started
    if result.timed_out:
        print(
            f"=== {label}: TIMEOUT after {elapsed:.1f}s; split this health command ===",
            flush=True,
        )
        return 124
    status = "passed" if result.return_code == 0 else f"failed ({result.return_code})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return result.return_code


def _run_critical_plan() -> int:
    plan = build_test_plan("critical")
    return run_test_plan(
        plan,
        RunOptions(
            state_root=REPO_ROOT / DEFAULT_STATE_ROOT_NAME,
            heartbeat_seconds=20.0,
        ),
    )


def main() -> int:
    for label, command in COMMANDS:
        code = _run(label, command)
        if code != 0:
            return code
    return _run_critical_plan()


if __name__ == "__main__":
    raise SystemExit(main())
