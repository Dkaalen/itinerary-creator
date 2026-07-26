from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app_modules"


def _imports(relative_path: str) -> set[str]:
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_mixed_session_transition_owner_is_deleted() -> None:
    assert not (APP / "session_transitions.py").exists()


def test_workflow_owners_do_not_import_upward_ui_or_repository_layers() -> None:
    for relative_path in (
        "app_modules/workflow_navigation.py",
        "app_modules/calculator_lifecycle.py",
        "app_modules/project_session_transitions.py",
        "app_modules/render_lifecycle.py",
        "app_modules/image_projection_state.py",
        "app_modules/calculator_action_policy.py",
    ):
        imports = _imports(relative_path)
        assert "streamlit" not in imports
        assert not any(name == "project_storage" or name.startswith("project_storage.") for name in imports)


def test_workflow_state_is_limited_to_defaults_reset_and_snapshot() -> None:
    source = (APP / "workflow_state.py").read_text(encoding="utf-8")
    for forbidden in (
        "def set_workflow_stage(",
        "def session_stage_from_state(",
        "def clear_pdf_artifacts(",
        "def mark_pdf_dirty(",
        "def image_grouped_days_from_state(",
    ):
        assert forbidden not in source


def test_calculator_page_delegates_action_policy_and_side_effects() -> None:
    source = (APP / "calculator_page.py").read_text(encoding="utf-8")
    assert "calculator_action_validation_issues" in source
    assert "calculator_action_updates_session_state" in source
    assert "dispatch_calculator_backend_action" in source
    assert "base64" not in source
    assert "CalculatorValidationScope" not in source
    assert "generate_itinerary_from_calculator" not in source
    assert "prepare_staged_calculation_download" not in source


def test_image_projection_is_read_only_and_render_lifecycle_does_not_match_images() -> None:
    image_source = (APP / "image_projection_state.py").read_text(encoding="utf-8")
    render_source = (APP / "render_lifecycle.py").read_text(encoding="utf-8")
    assert "state[" not in image_source
    assert "image_match" not in render_source
    assert "group_rows_by_day" not in render_source
