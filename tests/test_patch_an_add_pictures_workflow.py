from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_add_pictures_button_activates_pictures_without_browser_commit_handshake():
    source = (ROOT / "app_modules" / "main_view.py").read_text(encoding="utf-8")
    button_pos = source.index('st.button("Add pictures"')
    handler = source[button_pos: source.index('def render_final_preview_step', button_pos)]
    helper = source[source.index('def _activate_picture_stage'): source.index('def render_edit_page')]

    assert '_activate_picture_stage()' in handler
    assert 'set_pictures_added(st.session_state.output_edits, True)' in helper
    assert 'rebuild_current_preview(mark_pdf_dirty=True, force=True, save_html=True)' in helper
    assert '"_visual_editor_commit_counter"' not in handler
    assert '"_add_pictures_after_visual_edit_commit_nonce"] = next_nonce' not in handler
    assert '"_visual_editor_commit_counter"' not in helper
    assert '"_add_pictures_after_visual_edit_commit_nonce"] = next_nonce' not in helper


def test_visual_editor_picture_payload_uses_screen_sized_previews():
    workflow = (ROOT / "visual_editor_component" / "editor_workflow.py").read_text(encoding="utf-8")
    previews = (ROOT / "images" / "image_preview.py").read_text(encoding="utf-8")

    assert 'cover_theme["background_data_uri"] = get_image_preview_for_path' in workflow
    assert 'limit=12' in workflow
    assert 'max_size=(560, 380)' in previews
    assert 'quality=48' in previews
    assert 'max_size=(240, 170)' in previews
    assert 'quality=42' in previews
