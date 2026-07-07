from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text

from visual_editor_component.editor_workflow import (
    apply_visual_editor_result,
    build_visual_editor_payload,
    render_visual_editor,
)
from visual_editor_component import editor_autosave, editor_payload_builder, editor_result_applier

ROOT = Path(__file__).resolve().parents[1]


def test_visual_editor_workflow_is_a_small_facade():
    source = read_contract_text(ROOT / "visual_editor_component" / "editor_workflow.py")

    assert "def render_visual_editor" in source
    assert "from visual_editor_component.editor_payload_builder import" in source
    assert "from visual_editor_component.editor_result_applier import" in source
    assert "from visual_editor_component.editor_autosave import" in source
    assert len(source.splitlines()) < 140


def test_visual_editor_responsibilities_are_split_into_focused_modules():
    payload_source = read_contract_text(ROOT / "visual_editor_component" / "editor_payload_builder.py")
    result_source = read_contract_text(ROOT / "visual_editor_component" / "editor_result_applier.py")
    autosave_source = read_contract_text(ROOT / "visual_editor_component" / "editor_autosave.py")

    assert "def build_visual_editor_payload" in payload_source
    assert "def apply_visual_editor_result" in result_source
    assert "def try_apply_server_autosave" in autosave_source
    assert "def build_visual_editor_payload" not in result_source
    assert "def apply_visual_editor_result" not in payload_source


def test_legacy_editor_workflow_import_path_stays_stable():
    assert callable(build_visual_editor_payload)
    assert callable(apply_visual_editor_result)
    assert callable(render_visual_editor)
    assert editor_payload_builder.build_visual_editor_payload is build_visual_editor_payload
    assert editor_result_applier.apply_visual_editor_result is apply_visual_editor_result
    assert callable(editor_autosave.try_apply_server_autosave)


def test_visual_editor_save_does_not_synchronously_rebuild_preview():
    source = read_contract_text(ROOT / "visual_editor_component" / "editor_workflow.py")

    assert "Keep Save nearly instant" in source
    assert "rebuild_preview(mark_pdf_dirty=True)" not in source
