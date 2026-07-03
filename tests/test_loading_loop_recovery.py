from __future__ import annotations

from pathlib import Path

from app_modules.editor_commit import (
    ADD_PICTURES_COMMIT_REQUESTED_AT_KEY,
    PDF_COMMIT_REQUESTED_AT_KEY,
    VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY,
    add_pictures_editor_commit_elapsed_seconds,
    add_pictures_editor_commit_ready,
    add_pictures_editor_commit_timed_out,
    clear_add_pictures_editor_commit_request,
    pdf_editor_commit_ready,
    pdf_editor_commit_timed_out,
    request_add_pictures_editor_commit,
    request_pdf_editor_commit,
)
from app_modules.export_job_state import (
    auto_pdf_create_requested,
    consume_auto_pdf_create_request,
    request_auto_pdf_create,
    reset_export_job,
)
from app_modules.export_state import export_readiness_from_state
from tests.support.frontend_assets import frontend_script_names

READY_IMAGE_BANK = {
    "required_destinations_ready": True,
    "full_bank_found": True,
    "destination_image_count": 12,
}


def test_add_pictures_editor_commit_has_bounded_wait_state():
    state: dict[str, object] = {}

    nonce = request_add_pictures_editor_commit(state, now=100.0)

    assert state[ADD_PICTURES_COMMIT_REQUESTED_AT_KEY] == 100.0
    assert add_pictures_editor_commit_timed_out(state, now=119.0) is False
    assert add_pictures_editor_commit_timed_out(state, now=121.0) is True
    assert int(add_pictures_editor_commit_elapsed_seconds(state, now=121.0)) == 21

    state[VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY] = nonce
    state["_visual_editor_add_pictures_commit_ready"] = True
    assert add_pictures_editor_commit_ready(state) is True
    assert add_pictures_editor_commit_timed_out(state, now=999.0) is False

    clear_add_pictures_editor_commit_request(state)
    assert state.get(ADD_PICTURES_COMMIT_REQUESTED_AT_KEY) is None
    assert state.get("_add_pictures_after_visual_edit_commit_nonce") is None


def test_pdf_editor_commit_has_bounded_wait_state():
    state: dict[str, object] = {}

    nonce = request_pdf_editor_commit(state, now=10.0)

    assert state[PDF_COMMIT_REQUESTED_AT_KEY] == 10.0
    assert pdf_editor_commit_timed_out(state, now=29.0) is False
    assert pdf_editor_commit_timed_out(state, now=31.0) is True

    state[VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY] = nonce
    state["_visual_editor_export_commit_ready"] = True
    assert pdf_editor_commit_ready(state) is True
    assert pdf_editor_commit_timed_out(state, now=999.0) is False


def test_pdf_auto_create_queue_can_be_consumed_and_reset_on_blockers():
    state: dict[str, object] = {}
    request_auto_pdf_create(state)

    assert auto_pdf_create_requested(state) is True
    assert consume_auto_pdf_create_request(state) is True
    assert auto_pdf_create_requested(state) is False

    request_auto_pdf_create(state)
    reset_export_job(state)
    assert auto_pdf_create_requested(state) is False


def test_export_readiness_no_longer_exposes_dead_pending_editor_commit_field():
    readiness = export_readiness_from_state(
        {
            "itinerary_html": "<html></html>",
            "parsed_rows": [{"day": "Day 1"}],
            "output_edits": {"pictures_added": True},
            "preview_signature": "sig-1",
            "_pdf_after_visual_edit_commit_nonce": "stale",
            "_visual_editor_export_commit_ready": False,
        },
        READY_IMAGE_BANK,
    )

    assert not hasattr(readiness, "pending_editor_commit")
    assert "pending_editor_commit" not in readiness.as_dict()
    assert readiness.can_create_pdf is True


def test_visual_editor_warning_scripts_are_loaded_once():
    names = frontend_script_names()

    assert names.count("editor_warning_model.js") == 1
    assert names.count("editor_debug_readiness.js") == 1

    index_source = Path("visual_editor_component/frontend/index.html").read_text(encoding="utf-8")
    assert 'src="js/editor_warning_model.js"' not in index_source
    assert 'src="js/editor_debug_readiness.js"' not in index_source


def test_runtime_zip_fallback_download_is_bounded_by_network_timeout():
    source = Path("images/image_bank_fetch.py").read_text(encoding="utf-8")

    assert "socket.setdefaulttimeout(network_timeout_seconds())" in source
    assert "socket.setdefaulttimeout(previous_timeout)" in source
    assert 'status["timeout_seconds"] = network_timeout_seconds()' in source


def test_workflow_pages_surface_recovery_actions_for_commit_timeouts():
    preview_source = Path("app_modules/preview_step.py").read_text(encoding="utf-8")
    picture_source = Path("app_modules/picture_step.py").read_text(encoding="utf-8")
    export_source = Path("app_modules/export_step.py").read_text(encoding="utf-8")

    assert "add_pictures_editor_commit_timed_out" in preview_source
    assert "Retry save" in preview_source
    assert "add_pictures_last_error" in preview_source

    assert "pdf_editor_commit_timed_out" in picture_source
    assert "Create PDF from last saved version" in picture_source

    assert "pdf_editor_commit_timed_out" in export_source
    assert "PDF creation was stopped because the document is not ready" in export_source
