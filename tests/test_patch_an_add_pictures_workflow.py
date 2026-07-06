from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_add_pictures_is_gated_by_explicit_apply_changes_commit():
    edit_page = (ROOT / "app_modules" / "preview_step.py").read_text(encoding="utf-8")
    helper = edit_page[edit_page.index('def _activate_picture_stage'): edit_page.index('def _add_pictures_apply_ready')]

    action_source = (ROOT / "app_modules" / "image_stage_action.py").read_text(encoding="utf-8")
    commit_source = (ROOT / "app_modules" / "editor_commit.py").read_text(encoding="utf-8")

    assert 'start_workflow_transaction(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)' in edit_page
    assert 'workflow_transaction_state(st.session_state, WorkflowTransactionTarget.ADD_PICTURES)' in edit_page
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
    image_payloads = (ROOT / "visual_editor_component" / "editor_payload_images.py").read_text(encoding="utf-8")
    previews = (ROOT / "images" / "image_preview.py").read_text(encoding="utf-8")

    assert '_editor_cover_image_payload' in image_payloads
    assert 'image["data_uri"] = get_image_preview_for_path' in image_payloads
    assert 'DAY_REPLACEMENT_OPTION_LIMIT = 8' in image_payloads
    assert 'OPTION_PREVIEW_LIMIT = DAY_REPLACEMENT_OPTION_LIMIT' in image_payloads
    assert 'max_size=(560, 380)' in previews
    assert 'quality=48' in previews
    assert 'max_size=(240, 170)' in previews
    assert 'quality=42' in previews
