from pathlib import Path
from tests.support.static_contracts import read_contract_text
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_editor_exposes_save_and_recovery_status_panel():
    source = _frontend_source()

    assert "saveState" in source
    assert "saveRecoveryPanelHtml" in source
    assert "save-recovery-card" in source
    assert "saveStatusLabel" in source
    assert "saveStatusDetail" in source
    assert "Server autosave ready" not in source
    assert "saveIssuePanelHtml" in source


def test_editor_surfaces_local_recovery_and_failed_send_states():
    source = _frontend_source()

    assert "restoreLocalDraftIfAvailable" in source
    assert "restoredLocalDraftInfo" in source
    assert "safeSendComponentValue" in source
    assert "local_draft" in source
    assert "failed" in source
    assert "Could not send save to app" in source
    assert "recovered_full" in source


def test_editor_marks_dirty_pages_and_blocks():
    source = _frontend_source()

    assert "dirtyKeysForPage" in source
    assert "dirtyKeysForBlock" in source
    assert "pageHasDirtyEdits" in source
    assert "blockHasDirtyEdits" in source
    assert "outline-status dirty" in source
    assert "studioDirtyPagesMetric" in source


def test_server_autosave_status_is_in_payload_contract():
    payload_builder = read_contract_text("visual_editor_component/editor_payload_builder.py")
    status_helper = read_contract_text("visual_editor_component/editor_status.py")

    assert "persistent_draft_status" in payload_builder
    assert '"autosave_status"' in payload_builder
    assert "updated_at" in status_helper
    assert "persistent_draft_status()" in status_helper
