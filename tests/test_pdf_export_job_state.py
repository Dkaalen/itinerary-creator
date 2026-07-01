from app_modules.editor_commit import clear_pdf_editor_commit_request, request_pdf_editor_commit
from app_modules.export_job_state import (
    consume_auto_pdf_create_request,
    current_export_job,
    mark_export_failed,
    mark_export_ready,
    mark_exporting,
    request_auto_pdf_create,
    reset_export_job,
)


def test_pdf_export_auto_create_request_is_one_shot():
    state = {}

    request_auto_pdf_create(state)

    assert consume_auto_pdf_create_request(state) is True
    assert consume_auto_pdf_create_request(state) is False


def test_pdf_export_clears_completed_editor_commit_and_job_state_directly():
    state = {"preview_signature": "sig-1"}
    nonce = request_pdf_editor_commit(state)
    state["_visual_editor_export_commit_ready"] = True
    state["_visual_editor_last_applied_commit_nonce"] = nonce
    mark_exporting(state, signature="sig-1", now=100.0)

    clear_pdf_editor_commit_request(state)
    reset_export_job(state)

    assert state["_pdf_after_visual_edit_commit_nonce"] is None
    assert state["_visual_editor_export_commit_ready"] is False
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
