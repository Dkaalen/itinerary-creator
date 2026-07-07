"""Run a compact validation proof for cleanup batches.

This script intentionally avoids a single huge pytest process.  It runs the
runner lanes that previously produced timeout uncertainty through the same
stage-aware wrapper, then prints a JSON summary that can be pasted into patch
notes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProofCommand:
    label: str
    command: tuple[str, ...]
    timeout_seconds: int = 300


@dataclass(frozen=True)
class ProofResult:
    label: str
    return_code: int
    elapsed_seconds: float

    @property
    def ok(self) -> bool:
        return self.return_code == 0


def default_commands() -> tuple[ProofCommand, ...]:
    """Return timeout-safe proof commands for validation cleanup."""

    return (
        ProofCommand(
            "day-brain and sub-brain regression lane",
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_day_brain_copy.py",
                "tests/test_day_brain_intelligence.py",
                "tests/test_day_brain_proof_hardening.py",
                "tests/test_day_sub_brains.py",
            ),
        ),
        ProofCommand("hosted generation smoke", (sys.executable, "scripts/smoke_hosted_generation_path.py")),
        ProofCommand("output regression review", (sys.executable, "scripts/review_output_regression.py")),
    )


def run_command(command: ProofCommand) -> ProofResult:
    started = time.monotonic()
    completed = subprocess.run(
        command.command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        timeout=command.timeout_seconds,
        check=False,
    )
    return ProofResult(
        label=command.label,
        return_code=completed.returncode,
        elapsed_seconds=time.monotonic() - started,
    )


def build_plan() -> list[dict[str, object]]:
    return [
        {"label": command.label, "command": list(command.command), "timeout_seconds": command.timeout_seconds}
        for command in default_commands()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run cleanup validation proof commands.")
    parser.add_argument("--plan", action="store_true", help="Print the proof plan without executing it.")
    parser.add_argument("--include-group-tour", action="store_true", help="Also run the heavier group-tour rendering module.")
    args = parser.parse_args(argv)

    commands = list(default_commands())
    if args.include_group_tour:
        commands.append(ProofCommand("group-tour rendering", (sys.executable, "-m", "pytest", "-q", "tests/test_group_tour_rendering_regression.py")))

    if args.plan:
        print(json.dumps([{"label": command.label, "command": list(command.command), "timeout_seconds": command.timeout_seconds} for command in commands], indent=2))
        return 0

    results: list[ProofResult] = []
    for command in commands:
        print(f"\n=== {command.label} ===", flush=True)
        print(" ".join(command.command), flush=True)
        try:
            result = run_command(command)
        except subprocess.TimeoutExpired:
            result = ProofResult(command.label, 124, float(command.timeout_seconds))
        results.append(result)
        status = "PASS" if result.ok else f"FAIL({result.return_code})"
        print(f"=== {command.label}: {status} in {result.elapsed_seconds:.1f}s ===", flush=True)
        if not result.ok:
            break

    print(json.dumps([asdict(result) | {"ok": result.ok} for result in results], indent=2))
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
