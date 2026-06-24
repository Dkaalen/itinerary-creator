from pathlib import Path

from app_modules.export_state import export_readiness_from_state


READY_IMAGE_BANK = {
    "full_bank_found": True,
    "missing_full_bank": False,
    "destination_image_count": 12,
}
MISSING_IMAGE_BANK = {
    "full_bank_found": False,
    "missing_full_bank": True,
    "default_only": True,
}


def _ready_state(**overrides):
    state = {
        "itinerary_html": "<html></html>",
        "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
        "output_edits": {"pictures_added": True},
        "preview_signature": "sig-1",
        "pdf_bytes": None,
        "pdf_signature": None,
        "export_pdf_bytes": None,
        "export_pdf_signature": None,
        "_pdf_after_visual_edit_commit_nonce": None,
        "_visual_editor_export_commit_ready": False,
    }
    state.update(overrides)
    return state


def test_export_readiness_allows_create_only_after_document_pictures_and_real_image_bank():
    readiness = export_readiness_from_state(_ready_state(), READY_IMAGE_BANK)

    assert readiness.status_label == "Ready to create"
    assert readiness.can_create_pdf is True
    assert readiness.blocking_messages == ()


def test_export_readiness_blocks_missing_pictures_before_pdf_creation():
    readiness = export_readiness_from_state(_ready_state(output_edits={"pictures_added": False}), READY_IMAGE_BANK)

    assert readiness.can_create_pdf is False
    assert readiness.status_label == "Not ready"
    assert "Add destination pictures" in readiness.blocking_messages[0]


def test_export_readiness_blocks_default_only_image_bank():
    readiness = export_readiness_from_state(_ready_state(), MISSING_IMAGE_BANK)

    assert readiness.can_create_pdf is False
    assert readiness.image_bank_ready is False
    assert any("real destination image bank" in message for message in readiness.blocking_messages)


def test_export_readiness_tracks_persistent_pdf_artifact_by_signature():
    readiness = export_readiness_from_state(
        _ready_state(export_pdf_bytes=b"%PDF", export_pdf_signature="sig-1"),
        READY_IMAGE_BANK,
    )

    assert readiness.pdf_ready is True
    assert readiness.status_label == "PDF ready"
    assert readiness.can_create_pdf is True


def test_export_readiness_rejects_stale_pdf_artifact():
    readiness = export_readiness_from_state(
        _ready_state(export_pdf_bytes=b"%PDF", export_pdf_signature="old-sig"),
        READY_IMAGE_BANK,
    )

    assert readiness.pdf_ready is False
    assert readiness.status_label == "Ready to create"


def test_export_readiness_ignores_legacy_picture_review_state_before_pdf_creation():
    readiness = export_readiness_from_state(_ready_state(image_review_error_count=2), READY_IMAGE_BANK)

    assert readiness.can_create_pdf is True
    assert readiness.status_label == "Ready to create"
    assert not any("blocked picture selections" in message for message in readiness.blocking_messages)

def test_export_readiness_waits_for_visual_editor_commit():
    readiness = export_readiness_from_state(
        _ready_state(_pdf_after_visual_edit_commit_nonce="2", _visual_editor_export_commit_ready=False),
        READY_IMAGE_BANK,
    )

    assert readiness.can_create_pdf is False
    assert readiness.pending_editor_commit is True
    assert any("pending editor changes" in message for message in readiness.blocking_messages)


def test_export_screen_has_readiness_panel_and_disabled_create_gate():
    source = Path("app_modules/export_step.py").read_text()
    action_source = Path("app_modules/export_actions.py").read_text()
    state_source = Path("app_modules/export_state.py").read_text()
    styles = Path("ui/styles.py").read_text()

    assert "ExportReadiness" in state_source
    assert "def export_readiness_from_state" in state_source
    assert "def _render_export_readiness_panel" in source
    assert "disabled=not readiness.can_create_pdf" in source
    assert "picture_review_ready" not in state_source
    assert "image_bank_is_ready_for_client_pictures" in action_source
    assert "create_pdf_from_current_preview" in action_source
    assert ".export-readiness-panel" in styles
    assert ".export-readiness-grid" in styles


def test_export_screen_keeps_client_qa_out_of_normal_pdf_flow():
    source = Path("app_modules/export_step.py").read_text()

    assert "Client QA" not in source
    assert "Ready for client" not in source
    assert "Download QA" not in source
    assert "QA report" not in source
    assert "Export checks" in source
