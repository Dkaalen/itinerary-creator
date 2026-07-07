from __future__ import annotations

from collections.abc import Mapping

from app_modules.export_stage_action import enter_export_stage
from app_modules.editor_commit import request_add_pictures_editor_commit, VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY
from app_modules.image_stage_action import enter_picture_stage, retry_image_bank_connection
from app_modules.pdf_artifact_state import current_pdf_artifact, store_pdf_artifact
from app_modules.project_identity import active_project_id_from_state
from app_modules.workflow_state import ensure_workflow_defaults
from app_modules.export_identity import export_signature_for_state
from project_storage.delete_result import ProjectDeleteResult
from project_storage.project_browser import (
    delete_cloud_itinerary_result,
    download_cloud_project_file,
    list_cloud_calculation_files,
    list_cloud_itineraries,
    load_latest_cloud_project_payload,
)


def _state_ready_for_images() -> dict[str, object]:
    state: dict[str, object] = {}
    ensure_workflow_defaults(state)
    state.update(
        {
            "app_stage": "edit",
            "parsed_rows": [{"day": "Day 1", "type": "Activity", "city": "Oslo", "title": "Fjord Cruise"}],
            "output_edits": {"days": {"Day 1": {"title": "Oslo Fjord", "city": "Oslo"}}},
            "preview_signature": "preview-1",
        }
    )
    nonce = request_add_pictures_editor_commit(state, now=1.0)
    state[VISUAL_EDITOR_LAST_APPLIED_COMMIT_KEY] = nonce
    state["_visual_editor_add_pictures_commit_ready"] = True
    return state


def test_cloud_browser_contract_fails_safe_without_configured_repository(monkeypatch) -> None:
    monkeypatch.setattr("project_storage.project_browser.get_project_storage_repository", lambda: None)

    assert list_cloud_itineraries(search="Oslo") == ()
    assert list_cloud_calculation_files("missing") == ()
    assert download_cloud_project_file("missing/path.json") is None
    assert load_latest_cloud_project_payload("missing") is None
    assert delete_cloud_itinerary_result("missing") is None


def test_cloud_delete_reports_partial_storage_cleanup_failure() -> None:
    from project_storage.repository import ProjectStorageRepository
    from project_storage.config import SupabaseStorageConfig

    class FakeClient:
        def rest_get(self, table: str, params: Mapping[str, str]):
            assert table == "itinerary_files"
            return [{"storage_path": "itineraries/project-1/file.pdf"}]

        def rest_delete(self, table: str, params: Mapping[str, str]):
            assert table == "itineraries"
            assert params == {"id": "eq.project-1"}

        def storage_delete(self, bucket: str, paths: list[str]) -> None:
            raise RuntimeError("storage offline")

    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://example.supabase.co", secret_key="secret", bucket="private"),
        client=FakeClient(),
    )

    result = repository.delete_itinerary("project-1")

    assert isinstance(result, ProjectDeleteResult)
    assert result.record_deleted is True
    assert result.storage_files_deleted is False
    assert result.ok is True
    assert result.complete is False
    assert "storage offline" in result.storage_error


def test_image_stage_no_match_does_not_claim_picture_mode_or_reuse_pdf() -> None:
    state = _state_ready_for_images()
    signature = export_signature_for_state(state)
    if signature:
        store_pdf_artifact(state, content=b"stale", signature=signature)

    result = enter_picture_stage(
        state,
        status_func=lambda: {"required_destinations_ready": True},
        connect_func=lambda: {"required_destinations_ready": True},
        select_images_func=lambda grouped_days, output_edits: {},
        audit_images_func=lambda grouped_days, matches, output_edits: (),
        rebuild_preview_func=lambda **kwargs: True,
    )

    assert result.ok is False
    assert result.stage == "edit"
    assert state["output_edits"]["pictures_added"] is False
    assert state["pdf_status"] == "No destination pictures matched"
    assert current_pdf_artifact(state) is None


def test_image_stage_success_marks_pdf_dirty_and_enters_picture_review() -> None:
    state = _state_ready_for_images()

    result = enter_picture_stage(
        state,
        status_func=lambda: {"required_destinations_ready": True},
        connect_func=lambda: {"required_destinations_ready": True},
        select_images_func=lambda grouped_days, output_edits: {"Day 1": {"path": "images/oslo.jpg", "crop_focus": "center"}},
        audit_images_func=lambda grouped_days, matches, output_edits: (),
        rebuild_preview_func=lambda **kwargs: True,
    )

    assert result.ok is True
    assert result.stage == "pictures"
    assert state["output_edits"]["pictures_added"] is True
    assert state["pdf_status"] == "Needs refresh"
    assert state["day_image_matches"]["Day 1"]["path"] == "images/oslo.jpg"


def test_retry_image_bank_connection_never_moves_stage_on_failure() -> None:
    state = {"app_stage": "edit"}

    result = retry_image_bank_connection(
        state,
        status_func=lambda: {"ready": False, "blocking_message": "Missing images"},
        connect_func=lambda: {"ready": False, "blocking_message": "Missing images"},
    )

    assert result.ok is False
    assert result.stage == "edit"
    assert state["image_bank_gateway"]["ready"] is False


def test_export_stage_refreshes_project_snapshot_and_requests_auto_pdf(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("app_modules.export_stage_action.refresh_active_saved_project_current_snapshot", lambda state: calls.append("snapshot") or True)
    monkeypatch.setattr("app_modules.export_stage_action.request_auto_pdf_create", lambda state: calls.append("auto_pdf"))

    state = {"app_stage": "pictures", "active_project_storage_id": "project-1"}

    result = enter_export_stage(state, auto_create_pdf=True)

    assert result.ok is True
    assert result.stage == "export"
    assert state["app_stage"] == "export"
    assert calls == ["snapshot", "auto_pdf"]
    assert active_project_id_from_state(state) == "project-1"
