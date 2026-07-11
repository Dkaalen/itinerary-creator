"""Run a compact validation proof for cleanup batches.

This script intentionally avoids a single huge pytest process.  It runs the
runner lanes that previously produced timeout uncertainty through the same
stage-aware wrapper, then prints a JSON summary that can be pasted into patch
notes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.subprocess_control import run_controlled_process


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
    """Return timeout-safe proof commands for release-relevant regressions."""

    return (
        ProofCommand(
            "release truth regressions",
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_regressions_fixture_quality_transport.py::test_optional_arc_transfer_quality_gate",
                "tests/test_regressions_fixture_quality_transport.py::test_real_uploaded_inputs_quality_gate",
                "tests/test_ui22_qc4_arc1_scroll_and_quality.py::test_nin1_self_transfer_to_train_station_does_not_become_fake_train_route",
                "tests/test_extra_day_wrapper_rows.py",
                "tests/test_self_drive_truth_contract.py",
                "tests/test_output_truth_contracts.py",
            ),
        ),
        ProofCommand(
            "ownership and architecture guards",
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_architecture_guard_system.py",
                "tests/test_transport_model_architecture.py",
                "tests/test_destination_registry_regression.py",
            ),
        ),
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
                "tests/test_output_truth_contracts.py",
            ),
        ),
        ProofCommand(
            "group-tour role ownership",
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_group_tour_rendering_regression.py",
                "tests/test_preview_pdf_group_tours_regression.py",
                "tests/test_client_sanitizer_default_images_regression.py",
            ),
        ),
        ProofCommand(
            "activity identity contracts",
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_content_classification_priority.py",
                "tests/test_product_rule_registry.py",
                "tests/test_warning_ui_and_icebreaker_fidelity_quality_gate.py",
            ),
        ),
        ProofCommand(
            "journey and visit truth regressions",
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_output_quality_and_images_regression.py",
                "tests/test_real_output_quality_gate_iceland_regression.py",
                "tests/test_real_output_quality_gate_norway_regression.py",
                "tests/test_itinerary_stability_fidelity_repair.py",
                "tests/test_text_engine_consolidation_regression.py",
            ),
        ),
        ProofCommand("hosted generation smoke", (sys.executable, "scripts/smoke_hosted_generation_path.py")),
        ProofCommand("output regression review", (sys.executable, "scripts/review_output_regression.py")),
        ProofCommand("real Excel random quality check seed 6200", (sys.executable, "scripts/random_quality_check_itineraries.py", "--sample-size", "4", "--seed", "6200")),
        ProofCommand("real Excel score seed 7007", (sys.executable, "scripts/score_real_output_text.py", "--sample-size", "6", "--seed", "7007")),
        ProofCommand("real Excel score seed 9371", (sys.executable, "scripts/score_real_output_text.py", "--sample-size", "5", "--seed", "9371")),
        ProofCommand("preview PDF text parity", (sys.executable, "scripts/preview_pdf_text_guard.py", "--sample-size", "4", "--seed", "6200")),
    )


def run_command(command: ProofCommand) -> ProofResult:
    started = time.monotonic()
    completed = run_controlled_process(
        command.command,
        cwd=ROOT,
        timeout_seconds=command.timeout_seconds,
    )
    return ProofResult(
        label=command.label,
        return_code=completed.return_code,
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
        result = run_command(command)
        results.append(result)
        status = "PASS" if result.ok else f"FAIL({result.return_code})"
        print(f"=== {command.label}: {status} in {result.elapsed_seconds:.1f}s ===", flush=True)
        if not result.ok:
            break

    print(json.dumps([asdict(result) | {"ok": result.ok} for result in results], indent=2))
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
