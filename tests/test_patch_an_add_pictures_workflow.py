from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_add_pictures_is_gated_by_explicit_apply_changes_commit():
    source = (ROOT / "app_modules" / "main_view.py").read_text(encoding="utf-8")
    edit_page = source[source.index('def render_edit_page'): source.index('def render_final_preview_step')]
    helper = source[source.index('def _activate_picture_stage'): source.index('def _add_pictures_apply_ready')]

    action_source = (ROOT / "app_modules" / "workflow_actions.py").read_text(encoding="utf-8")
    commit_source = (ROOT / "app_modules" / "editor_commit.py").read_text(encoding="utf-8")

    assert 'request_add_pictures_editor_commit(st.session_state)' in edit_page
    assert 'if apply_ready:' in edit_page
    assert 'st.button("Add pictures", disabled=True' in edit_page
    assert 'Apply changes before adding pictures' in edit_page
    assert '_activate_picture_stage()' in edit_page
    assert 'enter_picture_stage(' in helper
    assert 'if not add_pictures_editor_commit_ready(state):' in action_source
    assert 'payload={"requires_apply_changes": True}' in action_source
    assert 'ADD_PICTURES_COMMIT_REQUEST_KEY' in commit_source
    assert 'ADD_PICTURES_COMMIT_READY_KEY' in commit_source
    assert 'set_pictures_added(output_edits, True)' in action_source
    assert 'rebuild_preview_func(mark_pdf_dirty=True, force=True, save_html=True)' in action_source


def test_visual_editor_picture_payload_uses_screen_sized_previews():
    workflow = (ROOT / "visual_editor_component" / "editor_payload_builder.py").read_text(encoding="utf-8")
    previews = (ROOT / "images" / "image_preview.py").read_text(encoding="utf-8")

    assert 'cover_theme["background_data_uri"] = get_image_preview_for_path' in workflow
    assert 'limit=12' in workflow
    assert 'max_size=(560, 380)' in previews
    assert 'quality=48' in previews
    assert 'max_size=(240, 170)' in previews
    assert 'quality=42' in previews
