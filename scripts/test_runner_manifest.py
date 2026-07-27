"""Authoritative executable test-plan manifest.

All staged runners, validation proof commands, and resume checkpoints consume
this module so test ownership cannot drift across several wrapper scripts.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

from scripts.test_catalogue import assert_test_catalogue_valid, assert_unique_stage_targets
from scripts.test_group_catalog import TEST_STAGE_BOUNDARY_SECONDS
from scripts.test_runner_models import TestPlanSpec, TestStageSpec
from scripts.test_runner_plans import RUNNER_GROUPS, _stages_for_group
from scripts.test_groups import group_descriptions

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTEST_STAGE_WORKER = "scripts/run_pytest_stage.py"
PROOF_PLAN_NAME = "proof"
AVAILABLE_PLAN_NAMES = (*RUNNER_GROUPS, PROOF_PLAN_NAME)

def _bounded_timeout(environment_name: str, default_seconds: int) -> int:
    requested = int(os.environ.get(environment_name, str(default_seconds)))
    return max(1, min(requested, TEST_STAGE_BOUNDARY_SECONDS))


FAST_TIMEOUT_SECONDS = _bounded_timeout("ITINERARY_TEST_FAST_TIMEOUT_SECONDS", 30)
QUALITY_TIMEOUT_SECONDS = _bounded_timeout("ITINERARY_TEST_QUALITY_TIMEOUT_SECONDS", TEST_STAGE_BOUNDARY_SECONDS)
RENDER_TIMEOUT_SECONDS = _bounded_timeout("ITINERARY_TEST_RENDER_TIMEOUT_SECONDS", TEST_STAGE_BOUNDARY_SECONDS)
SLOW_TIMEOUT_SECONDS = _bounded_timeout("ITINERARY_TEST_SLOW_TIMEOUT_SECONDS", TEST_STAGE_BOUNDARY_SECONDS)
COMMAND_TIMEOUT_SECONDS = _bounded_timeout("ITINERARY_TEST_COMMAND_TIMEOUT_SECONDS", TEST_STAGE_BOUNDARY_SECONDS)



def _workspace_fingerprint() -> str:
    """Fingerprint HEAD plus all tracked changes and untracked source inputs."""

    digest = hashlib.sha256()
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout
        diff = subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.split(b"\0")
        digest.update(head)
        digest.update(diff)
        for raw_path in sorted(path for path in untracked if path):
            relative = raw_path.decode("utf-8", errors="surrogateescape")
            path = REPO_ROOT / relative
            if not path.is_file():
                continue
            digest.update(raw_path)
            digest.update(path.read_bytes())
        return digest.hexdigest()
    except (OSError, subprocess.CalledProcessError):
        for path in sorted(REPO_ROOT.rglob("*.py")):
            if any(part in {".git", ".test-runs", "__pycache__"} for part in path.parts):
                continue
            digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text[:72] or "stage"


def _stage_id(index: int, label: str, command: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest()[:8]
    return f"{index:03d}-{_slug(label)}-{digest}"


def timeout_for_stage(label: str, targets: tuple[str, ...]) -> int:
    """Return a stage-local timeout based on actual workload ownership."""

    text = " ".join((label, *targets)).lower()
    if label.startswith("slow "):
        return SLOW_TIMEOUT_SECONDS
    if any(token in text for token in ("pdf", "render", "image", "playwright", "browser")):
        return RENDER_TIMEOUT_SECONDS
    if any(token in text for token in ("quality", "fixture", "corpus", "real_output")):
        return QUALITY_TIMEOUT_SECONDS
    return FAST_TIMEOUT_SECONDS


def pytest_stage_command(
    label: str,
    targets: tuple[str, ...],
    extra_args: tuple[str, ...],
    timeout_seconds: int,
) -> tuple[str, ...]:
    timeout_seconds = max(1, min(timeout_seconds, TEST_STAGE_BOUNDARY_SECONDS))
    args = [
        sys.executable,
        PYTEST_STAGE_WORKER,
        "--timeout-seconds",
        str(timeout_seconds),
        "--label",
        label,
        "--",
        "-q",
        "--durations=10",
    ]
    if label.startswith("slow "):
        args.append("-s")
    args.extend(targets)
    args.extend(extra_args)
    return tuple(args)


def _stage_group_id(plan_name: str, label: str) -> str:
    if plan_name not in {"full", "health", "release"}:
        return plan_name
    if label.startswith("fast safety"):
        return "fast"
    if label.startswith("pdf/rendering"):
        return "pdf"
    if label.startswith("remaining non-tiered"):
        return "remaining"
    prefix = label.split(" ", 1)[0]
    return prefix if prefix else plan_name


def _pytest_stage_specs(
    stage_rows: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    plan_name: str,
    extra_args: tuple[str, ...] = (),
) -> tuple[TestStageSpec, ...]:
    specs: list[TestStageSpec] = []
    for index, (label, targets) in enumerate(stage_rows, start=1):
        timeout_seconds = timeout_for_stage(label, targets)
        kind = "pytest"
        if label.startswith("slow ") and len(targets) == 1 and not extra_args:
            relative_path, separator, test_name = targets[0].partition("::")
            if separator and test_name:
                command = (
                    sys.executable,
                    "scripts/run_test_function_direct.py",
                    "--timeout-seconds",
                    str(timeout_seconds),
                    relative_path,
                    test_name,
                )
                kind = "direct-test"
            else:
                command = pytest_stage_command(label, targets, extra_args, timeout_seconds)
        else:
            command = pytest_stage_command(label, targets, extra_args, timeout_seconds)
        specs.append(
            TestStageSpec(
                stage_id=_stage_id(index, label, command),
                label=label,
                command=command,
                timeout_seconds=timeout_seconds,
                group_id=_stage_group_id(plan_name, label),
                kind=kind,
                targets=targets,
            )
        )
    return tuple(specs)


def _proof_pytest_groups() -> tuple[tuple[str, tuple[str, ...], int], ...]:
    return (
        (
            "release truth regressions",
            (
                "tests/test_regressions_fixture_quality_transport.py::test_optional_arc_transfer_quality_gate",
                "tests/test_regressions_fixture_quality_transport.py::test_real_uploaded_inputs_quality_gate",
                "tests/test_ui22_qc4_arc1_scroll_and_quality.py::test_nin1_self_transfer_to_train_station_does_not_become_fake_train_route",
                "tests/test_extra_day_wrapper_rows.py",
                "tests/test_self_drive_truth_contract.py",
                "tests/test_output_truth_contracts.py",
            ),
            QUALITY_TIMEOUT_SECONDS,
        ),
        (
            "ownership and architecture guards",
            (
                "tests/test_architecture_guard_system.py",
                "tests/test_transport_model_architecture.py",
                "tests/test_destination_registry_regression.py",
            ),
            FAST_TIMEOUT_SECONDS,
        ),
        (
            "day-brain and sub-brain regression lane",
            (
                "tests/test_day_brain_copy.py",
                "tests/test_day_brain_intelligence.py",
                "tests/test_day_brain_proof_hardening.py",
                "tests/test_day_sub_brains.py",
                "tests/test_output_truth_contracts.py",
            ),
            QUALITY_TIMEOUT_SECONDS,
        ),
        (
            "group-tour role ownership",
            (
                "tests/test_group_tour_rendering_regression.py",
                "tests/test_preview_pdf_group_tours_regression.py",
                "tests/test_client_sanitizer_default_images_regression.py",
            ),
            RENDER_TIMEOUT_SECONDS,
        ),
        (
            "activity identity contracts",
            (
                "tests/test_content_classification_priority.py",
                "tests/test_product_rule_registry.py",
                "tests/test_warning_ui_and_icebreaker_fidelity_quality_gate.py",
            ),
            FAST_TIMEOUT_SECONDS,
        ),
        (
            "journey and visit truth regressions",
            (
                "tests/test_output_quality_and_images_regression.py",
                "tests/test_real_output_quality_gate_iceland_regression.py",
                "tests/test_real_output_quality_gate_norway_regression.py",
                "tests/test_itinerary_stability_fidelity_repair.py",
                "tests/test_text_engine_consolidation_regression.py",
            ),
            QUALITY_TIMEOUT_SECONDS,
        ),
    )


def _proof_command_rows() -> tuple[tuple[str, tuple[str, ...], int], ...]:
    py = sys.executable
    return (
        ("hosted generation smoke", (py, "scripts/smoke_hosted_generation_path.py"), COMMAND_TIMEOUT_SECONDS),
        ("output regression review", (py, "scripts/review_output_regression.py"), COMMAND_TIMEOUT_SECONDS),
        ("real Excel random quality check seed 6200", (py, "scripts/random_quality_check_itineraries.py", "--sample-size", "4", "--seed", "6200"), QUALITY_TIMEOUT_SECONDS),
        ("real Excel score seed 7007", (py, "scripts/score_real_output_text.py", "--sample-size", "6", "--seed", "7007"), QUALITY_TIMEOUT_SECONDS),
        ("real Excel score seed 9371", (py, "scripts/score_real_output_text.py", "--sample-size", "5", "--seed", "9371"), QUALITY_TIMEOUT_SECONDS),
        ("preview PDF text parity", (py, "scripts/preview_pdf_text_guard.py", "--sample-size", "4", "--seed", "6200"), RENDER_TIMEOUT_SECONDS),
    )


def _chunked_proof_label(base_label: str, part: int, total: int) -> str:
    return base_label if part == 1 else f"{base_label} {part}/{total}"


def _proof_stage_specs() -> tuple[TestStageSpec, ...]:
    staged_rows: list[tuple[str, tuple[str, ...], int, str, tuple[str, ...]]] = []
    registered_targets: set[str] = set()
    for base_label, targets, timeout_seconds in _proof_pytest_groups():
        unique_targets = tuple(target for target in targets if target not in registered_targets)
        registered_targets.update(unique_targets)
        chunks = tuple(unique_targets[index : index + 2] for index in range(0, len(unique_targets), 2))
        for part, chunk in enumerate(chunks, start=1):
            label = _chunked_proof_label(base_label, part, len(chunks))
            command = pytest_stage_command(label, chunk, (), timeout_seconds)
            staged_rows.append((label, command, timeout_seconds, "pytest", chunk))
    for label, command, timeout_seconds in _proof_command_rows():
        staged_rows.append((label, command, timeout_seconds, "command", ()))

    return tuple(
        TestStageSpec(
            stage_id=_stage_id(index, label, command),
            label=label,
            command=command,
            timeout_seconds=timeout_seconds,
            group_id="proof",
            kind=kind,
            targets=targets,
        )
        for index, (label, command, timeout_seconds, kind, targets) in enumerate(staged_rows, start=1)
    )


def build_test_plan(plan_name: str, *, extra_pytest_args: tuple[str, ...] = ()) -> TestPlanSpec:
    """Build one validated, duplicate-free, bounded test plan."""

    assert_test_catalogue_valid(REPO_ROOT)
    if plan_name == PROOF_PLAN_NAME:
        if extra_pytest_args:
            raise ValueError("The proof plan does not accept extra pytest arguments.")
        stages = _proof_stage_specs()
        assert_unique_stage_targets(stages)
        return TestPlanSpec(
            name=plan_name,
            description="compact release proof using the same resumable orchestrator",
            stages=stages,
            workspace_fingerprint=_workspace_fingerprint(),
        )
    if plan_name not in RUNNER_GROUPS:
        raise ValueError(f"Unknown test plan {plan_name!r}.")
    stages = _pytest_stage_specs(
        _stages_for_group(plan_name),
        plan_name=plan_name,
        extra_args=extra_pytest_args,
    )
    assert_unique_stage_targets(stages)
    return TestPlanSpec(
        name=plan_name,
        description=group_descriptions().get(plan_name, "progress-tracked validation"),
        stages=stages,
        workspace_fingerprint=_workspace_fingerprint(),
    )
