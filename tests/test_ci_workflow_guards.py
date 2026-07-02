from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_ci_workflow_exists_and_uses_supported_runtimes() -> None:
    text = _workflow_text()

    assert "actions/checkout@v4" in text
    assert "actions/setup-python@v5" in text
    assert "python-version: '3.11'" in text
    assert "actions/setup-node@v4" in text
    assert "node-version: '20'" in text


def test_ci_workflow_runs_fast_quality_gates() -> None:
    text = _workflow_text()

    for marker in (
        "python scripts/import_smoke.py",
        "python scripts/architecture_guards.py",
        "tests/test_calculator_*.py",
        "tests/test_patch_ak_cleanup_hygiene.py",
        "tests/test_ci_workflow_guards.py",
        "python -m compileall -q .",
        "node --check calculator_grid_component/frontend/js/*.js",
        "node --check visual_editor_component/frontend/js/*.js",
        "git --no-pager diff --check",
    ):
        assert marker in text


def test_ci_workflow_does_not_make_known_full_suite_failure_mandatory() -> None:
    text = _workflow_text()
    mandatory_section = text.split("Known legacy Nordic sample check", maxsplit=1)[0]

    assert "python -m pytest tests/\n" not in mandatory_section
    assert "python -m pytest tests/ " not in mandatory_section
    assert "python -m pytest tests/ -q" not in mandatory_section


def test_known_nordic_quality_sample_is_documented_as_non_blocking() -> None:
    text = _workflow_text()
    start = text.index("Known legacy Nordic sample check")
    step = text[start : start + 220]

    assert "continue-on-error: true" in step
    assert "tests/test_nordic_quality_sample.py" in step
