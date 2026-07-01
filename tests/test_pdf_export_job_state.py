from app_modules.export_editor_save import (
    PDF_EDITOR_SAVE_TIMEOUT_SECONDS,
    clear_pdf_editor_save,
    pdf_editor_save_elapsed_seconds,
    pdf_editor_save_timed_out,
    pdf_editor_save_waiting,
    request_editor_save_before_pdf,
)
from app_modules.export_job_state import (
    consume_auto_pdf_create_request,
    current_export_job,
    mark_export_failed,
    mark_export_ready,
    mark_exporting,
    request_auto_pdf_create,
)


def test_pdf_export_auto_create_request_is_one_shot():
    state = {}

    request_auto_pdf_create(state)

    assert consume_auto_pdf_create_request(state) is True
    assert consume_auto_pdf_create_request(state) is False


def test_pdf_editor_save_request_is_no_wait_compatibility_path():
    state = {"preview_signature": "sig-1", "_pdf_after_visual_edit_commit_nonce": "legacy"}

    job = request_editor_save_before_pdf(state, now=100.0)

    assert job.exporting is True
    assert job.signature == "sig-1"
    assert state["_pdf_after_visual_edit_commit_nonce"] is None
    assert pdf_editor_save_waiting(state) is False
    assert pdf_editor_save_elapsed_seconds(state, now=104.0) == 0.0
    assert not pdf_editor_save_timed_out(state, now=100.0 + PDF_EDITOR_SAVE_TIMEOUT_SECONDS + 0.1)

    clear_pdf_editor_save(state)

    assert pdf_editor_save_waiting(state) is False
    assert current_export_job(state).state == "idle"


def test_pdf_export_job_tracks_export_ready_and_failed_states():
    state = {}

    exporting = mark_exporting(state, signature="sig-1", now=10.0)
    ready = mark_export_ready(state, signature="sig-1", now=12.0)
    failed = mark_export_failed(state, error="boom", now=15.0)

    assert exporting.exporting is True
    assert ready.ready is True
    assert ready.signature == "sig-1"
    assert failed.failed is True
    assert failed.error == "boom"
