from __future__ import annotations

import re
from pathlib import Path

from scripts.test_groups import CI_MATRIX_GROUPS

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _job_block(job_name: str) -> str:
    text = _workflow_text()
    match = re.search(rf"^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)", text, re.M | re.S)
    assert match, f"Missing CI job: {job_name}"
    return match.group("body")


def _matrix_groups() -> tuple[str, ...]:
    block = _job_block("test-groups")
    match = re.search(r"group:\n(?P<body>(?:\s+- [a-zA-Z0-9_-]+\n)+)", block)
    assert match, "test-groups job must define a group matrix"
    return tuple(re.findall(r"- ([a-zA-Z0-9_-]+)", match.group("body")))


def test_ci_workflow_exists_and_uses_supported_runtimes() -> None:
    text = _workflow_text()

    assert "actions/checkout@v4" in text
    assert "actions/setup-python@v5" in text
    assert "python-version: '3.13'" in text
    assert "actions/setup-node@v4" in text
    assert "node-version: '20'" in text


def test_ci_workflow_runs_real_health_gates() -> None:
    block = _job_block("health-gates")

    expected_commands = (
        "python scripts/import_smoke.py",
        "python scripts/architecture_guards.py",
        "python -m pytest tests/test_architecture_guard_system.py -q",
        "tests/test_test_runner_groups.py",
        "tests/test_ci_workflow_guards.py",
        "python -m compileall -q .",
        "python -m pytest --collect-only -q",
        "python scripts/test_suite_audit.py",
        "node --check calculator_grid_component/frontend/js/*.js",
        "node --check visual_editor_component/frontend/js/*.js",
        "git --no-pager diff --check",
    )
    for command in expected_commands:
        assert command in block


def test_ci_matrix_covers_all_timeout_safe_product_lanes() -> None:
    assert _matrix_groups() == CI_MATRIX_GROUPS
    block = _job_block("test-groups")

    assert "fail-fast: false" in block
    assert "python scripts/run_test_group.py ${{ matrix.group }}" in block


def test_pdf_and_quality_are_required_but_isolated_from_main_matrix() -> None:
    matrix_groups = set(_matrix_groups())
    assert "pdf" not in matrix_groups
    assert "quality" not in matrix_groups

    assert "python scripts/run_test_group.py pdf" in _job_block("pdf-group")
    assert "python scripts/run_test_group.py quality" in _job_block("quality-group")


def test_ci_workflow_keeps_full_and_slow_out_of_required_gates() -> None:
    text = _workflow_text()

    assert "python scripts/run_test_group.py full" not in text
    assert "python scripts/run_test_group.py slow" not in text
    assert "python -m pytest tests/ -q" not in text


def test_nordic_quality_sample_is_a_required_gate() -> None:
    block = _job_block("nordic-quality-sample")

    assert "continue-on-error: true" not in block
    assert "tests/test_nordic_quality_sample.py" in block


def test_ci_workflow_sets_honest_timeout_and_buffering_env() -> None:
    text = _workflow_text()

    assert "PYTHONUNBUFFERED: '1'" in text
    assert "ITINERARY_TEST_STAGE_TIMEOUT_SECONDS: '300'" in text
    assert "ITINERARY_RELEASE_STEP_TIMEOUT_SECONDS: '900'" in text
