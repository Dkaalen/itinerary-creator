from pathlib import Path


def test_export_step_uses_shared_recoverable_pdf_job_flow():
    source = Path("app_modules/export_step.py").read_text(encoding="utf-8")

    assert "request_editor_save_before_pdf(st.session_state)" not in source
    assert "Create PDF from last saved version" not in source
    assert "Saving the latest editor changes before creating the PDF" not in source
    assert "clear_pdf_editor_save(st.session_state)" in source
    assert "Applying pending editor changes" not in source
    assert "visual_editor_export_commit_ready" not in source
    assert "current_export_job" in source


def test_picture_page_create_pdf_enters_export_with_one_shot_auto_request():
    picture_source = Path("app_modules/picture_step.py").read_text(encoding="utf-8")
    action_source = Path("app_modules/export_stage_action.py").read_text(encoding="utf-8")

    assert "enter_export_stage(st.session_state, auto_create_pdf=True)" in picture_source
    assert "auto_create_pdf: bool = False" in action_source
    assert "request_auto_pdf_create(state)" in action_source
    assert "request_pdf_commit_func" in action_source


def test_pdf_export_avoids_repeated_image_bank_storage_scans_on_normal_path():
    export_source = Path("app_modules/export_step.py").read_text(encoding="utf-8")
    image_source = Path("app_modules/export_image_validation.py").read_text(encoding="utf-8")
    gateway_source = Path("app_modules/image_gateway_ui.py").read_text(encoding="utf-8")

    assert "image_bank_storage_signature" not in export_source
    assert "image_bank_storage_signature" not in image_source
    assert "image_bank_storage_signature" not in gateway_source
    assert "get_cached_image_bank_status" in export_source
    assert "get_cached_image_bank_status" in image_source


def test_pdf_export_timing_is_internal_and_stage_based():
    source = Path("app_modules/export_actions.py").read_text(encoding="utf-8")
    timing_source = Path("app_modules/export_timing.py").read_text(encoding="utf-8")

    assert "reset_pdf_export_timings" in source
    assert "record_pdf_export_stage" in source
    assert "prepare_images" in source
    assert "render_pdf" in source
    assert "PDF_EXPORT_TIMINGS_KEY" in timing_source
    assert "st." not in timing_source


def test_editor_save_keeps_dirty_keys_until_server_payload_acknowledges_them():
    state_source = Path("visual_editor_component/frontend/js/state.js").read_text(encoding="utf-8")
    save_source = Path("visual_editor_component/frontend/js/editor_save_state.js").read_text(encoding="utf-8")
    editing_source = Path("visual_editor_component/frontend/js/editing.js").read_text(encoding="utf-8")
    render_source = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")

    assert "pendingServerSaveKeys" in state_source
    assert "acknowledgeServerSaveFromPayload" in save_source
    assert "serverPayloadContainsPendingSave" in save_source
    assert "pendingServerSaveKeys = new Set(touchedKeys)" in editing_source
    assert "acknowledgeServerSaveFromPayload(initialPayload)" in render_source
    assert "if (!safeSendComponentValue(serialized, commitNonce ? 'exporting' : 'saving')) return;\n  touchedKeys = new Set();" not in editing_source
