from __future__ import annotations

from pathlib import Path

from scripts.run_test_group import (
    RUNNER_GROUPS,
    _extract_runner_flags,
    _pytest_command,
    _pytest_env,
    _stages_for_group,
)

from scripts.test_groups import (
    GROUPS,
    GROUP_ORDER,
    build_full_stages,
    build_slow_stages,
    focused_group_names,
    group_descriptions,
    empty_legacy_test_modules,
    missing_group_paths,
    pdf_module_names,
    quality_module_names,
    slow_module_names,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _module_name(path: str) -> str:
    module_path = str(path).partition("::")[0]
    return Path(module_path).name


def test_named_test_group_paths_exist() -> None:
    assert missing_group_paths(REPO_ROOT) == ()


def test_full_test_plan_covers_every_test_module() -> None:
    discovered = {
        path.name
        for path in (REPO_ROOT / "tests").glob("test_*.py")
        if path.name not in empty_legacy_test_modules()
    }
    planned: list[str] = []

    for _stage_name, paths in build_full_stages(REPO_ROOT):
        planned.extend(_module_name(path) for path in paths)

    assert set(planned) == discovered

    split_modules = {"test_regressions_fixture_quality.py"}
    unsplit_modules = [module for module in planned if module not in split_modules]
    assert len(unsplit_modules) == len(set(unsplit_modules))


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
    expected_scripts = {
        "fast": "run_fast_tests.ps1",
        "parser": "run_parser_tests.ps1",
        "activity": "run_activity_tests.ps1",
        "architecture": "run_architecture_tests.ps1",
        "calculator": "run_calculator_tests.ps1",
        "editor": "run_editor_tests.ps1",
        "images": "run_image_tests.ps1",
        "storage": "run_storage_tests.ps1",
        "ui": "run_ui_tests.ps1",
        "workflow": "run_workflow_tests.ps1",
        "quality": "run_quality_tests.ps1",
        "pdf": "run_pdf_tests.ps1",
        "full": "run_full_tests.ps1",
    }

    for group, script in expected_scripts.items():
        text = (REPO_ROOT / "scripts" / script).read_text(encoding="utf-8")
        assert "run_test_group.py" in text
        assert f"run_test_group.py {group}" in text


def test_runner_accepts_every_documented_group() -> None:
    assert RUNNER_GROUPS == (*GROUP_ORDER, "full")
    assert set(group_descriptions()) == set(GROUPS)


def test_focused_groups_exist_for_common_patch_areas() -> None:
    assert focused_group_names() == (
        "parser",
        "activity",
        "architecture",
        "calculator",
        "editor",
        "images",
        "storage",
        "ui",
        "workflow",
    )
    for name in focused_group_names():
        assert GROUPS[name]
        assert name in group_descriptions()


def test_plan_mode_uses_same_stage_builder_as_runner() -> None:
    fast_stages = _stages_for_group("fast")

    assert len(fast_stages) > 1
    assert all(name.startswith("fast") for name, _paths in fast_stages)
    assert _stages_for_group("activity") == (("activity", GROUPS["activity"]),)
    assert len(_stages_for_group("architecture")) > 1
    assert len(_stages_for_group("calculator")) > 1
    assert len(_stages_for_group("storage")) > 1
    assert len(_stages_for_group("workflow")) > 1
    assert len(_stages_for_group("editor")) > 1
    assert len(_stages_for_group("images")) > 1
    assert len(_stages_for_group("ui")) > 1
    assert len(_stages_for_group("pdf")) > 1
    assert all(len(paths) <= 3 for _name, paths in _stages_for_group("pdf"))
    assert _stages_for_group("full") == build_full_stages(REPO_ROOT)
    assert _stages_for_group("slow") == build_slow_stages()



def test_runner_plan_flags_do_not_leak_into_pytest_args() -> None:
    assert _extract_runner_flags(["activity", "--plan"]) == (["activity"], False, True)
    assert _extract_runner_flags(["--list-groups"]) == ([], True, False)
    assert _extract_runner_flags(["activity", "--", "--plan"]) == (
        ["activity", "--", "--plan"],
        False,
        False,
    )

def test_slow_group_runs_each_stability_target_in_its_own_stage() -> None:
    stages = build_slow_stages()
    flattened_targets = [paths[0] for _name, paths in stages]

    assert len(stages) > len(GROUPS["slow"])
    assert "tests/test_broad_logic_stress_regressions.py" in flattened_targets
    assert "tests/test_regressions_fixture_quality.py::test_v36c57_real_uploaded_inputs_quality_gate" in flattened_targets
    assert all(len(paths) == 1 for _name, paths in stages)
    assert all(name.startswith("slow ") for name, _paths in stages)


def test_slow_runner_disables_pytest_capture() -> None:
    command = _pytest_command("slow 1/1: test_example.py", ("tests/test_example.py",), [])

    assert "-s" in command
    assert command.index("-s") < command.index("tests/test_example.py")


def test_non_slow_runner_keeps_default_capture() -> None:
    command = _pytest_command("quality", ("tests/test_example.py",), [])

    assert "-s" not in command


def test_runner_disables_external_pytest_plugin_autoload(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)

    assert _pytest_env()["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"


def test_runner_respects_explicit_pytest_plugin_autoload_env(monkeypatch) -> None:
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "0")

    assert _pytest_env()["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "0"


def test_slow_harness_uses_configured_slow_modules() -> None:
    from scripts.run_slow_tests import _slow_targets

    discovered_modules = {target[0] for target in _slow_targets()}

    assert discovered_modules == set(GROUPS["slow"])
