from __future__ import annotations

from pathlib import Path

from scripts.test_groups import (
    GROUPS,
    build_full_stages,
    empty_legacy_test_modules,
    missing_group_paths,
    pdf_module_names,
    quality_module_names,
    slow_module_names,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _module_name(path: str) -> str:
    return Path(path).name


def test_named_test_group_paths_exist() -> None:
    assert missing_group_paths(REPO_ROOT) == ()


def test_full_test_plan_covers_every_test_module_once() -> None:
    discovered = {
        path.name
        for path in (REPO_ROOT / "tests").glob("test_*.py")
        if path.name not in empty_legacy_test_modules()
    }
    planned: list[str] = []

    for _stage_name, paths in build_full_stages(REPO_ROOT):
        planned.extend(_module_name(path) for path in paths)

    assert set(planned) == discovered
    assert len(planned) == len(set(planned))


def test_empty_legacy_modules_are_documented_placeholders() -> None:
    for module_name in empty_legacy_test_modules():
        text = (REPO_ROOT / "tests" / module_name).read_text(encoding="utf-8")
        assert "Legacy" in text


def test_marker_sets_stay_aligned_with_named_groups() -> None:
    assert pdf_module_names() == {_module_name(path) for path in GROUPS["pdf"]}
    assert slow_module_names() == {_module_name(path) for path in GROUPS["slow"]}

    # The quality marker intentionally includes both the day-to-day quality gate
    # and the larger fixture-quality modules that only run in full/slow lanes.
    assert {_module_name(path) for path in GROUPS["quality"]}.issubset(quality_module_names())


def test_powershell_runners_delegate_to_shared_python_runner() -> None:
    for script in (
        "run_fast_tests.ps1",
        "run_quality_tests.ps1",
        "run_pdf_tests.ps1",
        "run_full_tests.ps1",
    ):
        text = (REPO_ROOT / "scripts" / script).read_text(encoding="utf-8")
        assert "run_test_group.py" in text
