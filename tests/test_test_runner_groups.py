from __future__ import annotations

from pathlib import Path

from tests.support.static_contracts import read_contract_text
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
    HEALTH_CHECK_GROUPS,
    RELEASE_CANDIDATE_GROUPS,
    CHUNKED_GROUP_STAGE_SIZES,
    build_full_stages,
    build_slow_stages,
    critical_module_names,
    fast_module_names,
    focused_group_names,
    group_descriptions,
    empty_legacy_test_modules,
    missing_group_paths,
    pdf_module_names,
    quality_module_names,
    slow_direct_targets,
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

    split_modules = slow_module_names()
    unsplit_modules = [module for module in planned if module not in split_modules]
    assert len(unsplit_modules) == len(set(unsplit_modules))


def test_empty_legacy_modules_are_documented_placeholders() -> None:
    for module_name in empty_legacy_test_modules():
        module_body = read_contract_text(REPO_ROOT / "tests" / module_name)
        assert "Legacy" in module_body


def test_marker_sets_stay_aligned_with_named_groups() -> None:
    assert pdf_module_names() == {_module_name(path) for path in GROUPS["pdf"]}
    assert slow_module_names() == {_module_name(path) for path in GROUPS["slow"]}

    # The quality marker intentionally includes both the day-to-day quality gate
    # and the larger fixture-quality modules that only run in full/slow lanes.
    assert {_module_name(path) for path in GROUPS["quality"]}.issubset(quality_module_names())


def test_critical_group_is_free_of_pdf_slow_and_large_quality_modules() -> None:
    heavy_modules = pdf_module_names() | slow_module_names() | quality_module_names()

    assert critical_module_names().isdisjoint(heavy_modules)


def test_fast_group_is_free_of_pdf_slow_and_large_quality_modules() -> None:
    heavy_modules = pdf_module_names() | slow_module_names() | quality_module_names()

    assert fast_module_names().isdisjoint(heavy_modules)


def test_pdf_group_excludes_isolated_slow_modules() -> None:
    assert pdf_module_names().isdisjoint(slow_module_names())


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
        "health": "run_health_check.ps1",
        "release": "run_release_candidate_tests.ps1",
        "full": "run_full_tests.ps1",
    }

    for group, script in expected_scripts.items():
        script_body = read_contract_text(REPO_ROOT / "scripts" / script)
        assert "run_test_group.py" in script_body or f"run_{group}" in script_body
        if group in GROUPS or group == "full":
            assert f"run_test_group.py {group}" in script_body


def test_runner_accepts_every_documented_group() -> None:
    assert RUNNER_GROUPS == (*GROUP_ORDER, "health", "release", "full")
    assert set(GROUPS).issubset(group_descriptions())
    assert "health" in group_descriptions()
    assert "release" in group_descriptions()


def test_focused_groups_exist_for_common_patch_areas() -> None:
    assert focused_group_names() == (
        "critical",
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


def test_health_and_release_groups_have_clear_scope() -> None:
    assert HEALTH_CHECK_GROUPS == ("critical",)
    assert RELEASE_CANDIDATE_GROUPS == (
        "critical",
        "fast",
        "calculator",
        "storage",
        "workflow",
        "parser",
        "activity",
        "architecture",
        "editor",
        "images",
        "ui",
        "quality",
        "pdf",
    )
    assert "slow" not in RELEASE_CANDIDATE_GROUPS


def test_plan_mode_uses_same_stage_builder_as_runner() -> None:
    for group_name, max_stage_size in CHUNKED_GROUP_STAGE_SIZES.items():
        stages = _stages_for_group(group_name)
        assert stages
        assert all(name.startswith(group_name) for name, _paths in stages)
        assert all(len(paths) <= max_stage_size for _name, paths in stages)
        assert [path for _name, paths in stages for path in paths] == list(GROUPS[group_name])

    assert _stages_for_group("health") == _stages_for_group("critical")
    assert _stages_for_group("full") == build_full_stages(REPO_ROOT)
    assert _stages_for_group("slow") == build_slow_stages()


def test_release_plan_is_composed_from_timeout_safe_groups() -> None:
    release_stages = _stages_for_group("release")
    release_targets = [path for _name, paths in release_stages for path in paths]

    assert release_stages
    assert not any(path.startswith("tests/test_real_fixture_quality_gate.py::") for path in release_targets)
    assert not any(name.startswith("slow ") for name, _paths in release_stages)


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

    assert flattened_targets == list(slow_direct_targets(REPO_ROOT))
    assert len(stages) == len(slow_direct_targets(REPO_ROOT))
    assert len(stages) > 29
    assert "tests/test_broad_logic_stress_regressions.py::test_daytime_train_preserves_seat_quantity_without_raw_supplier_title" in flattened_targets
    assert "tests/test_regressions_fixture_quality_transport.py::test_real_uploaded_inputs_quality_gate" in flattened_targets
    assert all(len(paths) == 1 for _name, paths in stages)
    assert all(name.startswith("slow ") for name, _paths in stages)





def test_real_fixture_slow_split_matches_fixture_manifest() -> None:
    import importlib
    from scripts.test_group_catalog.quality import (
        REAL_FIXTURE_QUALITY_FILES,
        SLOW_TEST_SPLITS,
    )

    module = importlib.import_module("tests.test_real_fixture_quality_gate")
    split_names = SLOW_TEST_SPLITS["tests/test_real_fixture_quality_gate.py"]
    assert len(split_names) == len(REAL_FIXTURE_QUALITY_FILES)
    assert all(callable(getattr(module, name, None)) for name in split_names)

def test_slow_runner_uses_subprocess_loop_not_exec_chain() -> None:
    import scripts.run_slow_tests as slow_runner

    assert hasattr(slow_runner, "run_slow_targets")
    assert not hasattr(slow_runner, "_exec_next")


def test_slow_runner_plan_matches_group_targets() -> None:
    import scripts.run_slow_tests as slow_runner

    targets = [f"{path}::{name}" for path, name in slow_runner._slow_targets(REPO_ROOT)]

    assert targets == list(slow_direct_targets(REPO_ROOT))


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


def test_slow_harness_uses_exact_slow_direct_targets() -> None:
    from scripts.run_slow_tests import _slow_targets

    assert [f"{path}::{name}" for path, name in _slow_targets()] == list(slow_direct_targets(REPO_ROOT))


def test_controlled_subprocess_timeout_terminates_worker_tree() -> None:
    import sys
    import time
    from scripts.subprocess_control import run_controlled_process

    started = time.monotonic()
    result = run_controlled_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        timeout_seconds=0.1,
    )

    assert result.return_code == 124
    assert result.timed_out
    assert time.monotonic() - started < 6
