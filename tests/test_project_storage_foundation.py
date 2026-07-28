from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text

from calculator.calculator_state import CalculatorState
from project_storage.config import supabase_config_from_mapping
from project_storage.paths import calculator_workbook_path, itinerary_snapshot_path, pdf_export_path, safe_segment
from project_storage.repository import ProjectStorageRepository
from app_modules.project_storage_workflow import ensure_storage_itinerary, save_calculation_workbook, save_project_payload_snapshot


class FakeClient:
    def __init__(self) -> None:
        self.rest_inserts = []
        self.rest_gets = []
        self.uploads = []
        self.downloads = []
        self.storage_deletes = []
        self.rest_deletes = []
        self.fail_upload: Exception | None = None
        self.fail_register_file: Exception | None = None
        self.fail_create_version: Exception | None = None
        self.fail_itinerary_upsert: Exception | None = None
        self.fail_storage_delete: Exception | None = None

    def rest_insert(self, table, payload, *, upsert=False):
        if table == "itineraries" and self.fail_itinerary_upsert is not None:
            raise self.fail_itinerary_upsert
        if table == "itinerary_versions" and self.fail_create_version is not None:
            raise self.fail_create_version
        if table == "itinerary_files" and self.fail_register_file is not None:
            raise self.fail_register_file
        self.rest_inserts.append((table, payload, upsert))
        row = {**payload}
        row.setdefault("id", f"{table}-id")
        return [row]

    def rest_get(self, table, params):
        self.rest_gets.append((table, params))
        return [{"version_number": 3}]

    def storage_upload(self, bucket, storage_path, content, *, content_type):
        if self.fail_upload is not None:
            raise self.fail_upload
        self.uploads.append((bucket, storage_path, content, content_type))

    def storage_download(self, bucket, storage_path):
        self.downloads.append((bucket, storage_path))
        return b"downloaded"

    def storage_delete(self, bucket, storage_paths):
        if self.fail_storage_delete is not None:
            raise self.fail_storage_delete
        self.storage_deletes.append((bucket, storage_paths))

    def rest_delete(self, table, params):
        self.rest_deletes.append((table, params))
        return []


def test_supabase_config_accepts_flat_streamlit_secrets_and_strips_rest_suffix() -> None:
    config = supabase_config_from_mapping(
        {
            "SUPABASE_URL": "https://abc.supabase.co/rest/v1/",
            "SUPABASE_SECRET_KEY": "sb_secret_test",
            "SUPABASE_BUCKET": "itinerary-files",
        }
    )

    assert config is not None
    assert config.url == "https://abc.supabase.co"
    assert config.secret_key == "sb_secret_test"
    assert config.bucket == "itinerary-files"


def test_storage_paths_group_files_under_itinerary_id() -> None:
    itinerary_id = "11111111-2222-3333-4444-555555555555"

    assert calculator_workbook_path(itinerary_id, "Norway Winter.xlsx").startswith(
        f"itineraries/{itinerary_id}/calculator/"
    )
    assert itinerary_snapshot_path(itinerary_id, "booknordics_customer", 2) == (
        f"itineraries/{itinerary_id}/snapshots/booknordics_customer-v002.json"
    )
    assert pdf_export_path(itinerary_id, "agent", "Final PDF.pdf").startswith(
        f"itineraries/{itinerary_id}/exports/agent/"
    )
    assert safe_segment("bad / file:name.xlsx") == "bad-file-name.xlsx"


def test_repository_writes_itinerary_versions_and_file_records() -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )

    assert repository.next_version_number("itinerary-id", "agent") == 4
    repository.upsert_itinerary("itinerary-id", name="Norway Winter")
    version = repository.create_version(
        itinerary_id="itinerary-id",
        version_number=4,
        itinerary_type="agent",
        source_type="generated_itinerary",
        payload={"ok": True},
    )
    repository.upload_file("itineraries/itinerary-id/snapshots/agent-v004.json", b"{}", content_type="application/json")
    repository.register_file(
        itinerary_id="itinerary-id",
        version_id=version["id"],
        file_type="generated_itinerary_json",
        filename="agent-v004.json",
        storage_path="itineraries/itinerary-id/snapshots/agent-v004.json",
    )

    table, payload, upsert = fake.rest_inserts[0]
    assert table == "itineraries"
    assert payload["id"] == "itinerary-id"
    assert payload["name"] == "Norway Winter"
    assert payload["status"] == "draft"
    assert "updated_at" in payload
    assert upsert is True
    assert fake.uploads[0][0] == "itinerary-files"
    assert fake.rest_inserts[-1][0] == "itinerary_files"


def test_workflow_hook_reuses_existing_itinerary_id(monkeypatch) -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )
    monkeypatch.setattr("app_modules.project_storage_workflow.get_project_storage_repository", lambda: repository)
    app_state = {
        "active_project_storage_id": "11111111-2222-3333-4444-555555555555",
        "active_project_cloud_persisted": True,
    }
    calculator_state = CalculatorState(itinerary_name="Norway Winter", rows=())

    assert save_calculation_workbook(
        app_state,
        calculator_state,
        content=b"xlsx",
        filename="Norway Winter.xlsx",
        currency_rates={"EUR": 1.0},
    )

    assert app_state["active_project_storage_id"] == "11111111-2222-3333-4444-555555555555"
    assert app_state["project_storage_last_calculator_file_path"].startswith(
        "itineraries/11111111-2222-3333-4444-555555555555/calculator/"
    )
    assert fake.uploads[0][2] == b"xlsx"


def test_unsaved_project_does_not_create_cloud_calculator_file(monkeypatch) -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )
    monkeypatch.setattr("app_modules.project_storage_workflow.get_project_storage_repository", lambda: repository)
    app_state = {"active_project_storage_id": "new-unsaved-id"}

    assert save_calculation_workbook(
        app_state,
        CalculatorState(itinerary_name="Unsaved", rows=()),
        content=b"xlsx",
        filename="Unsaved.xlsx",
    ) is False
    assert fake.rest_inserts == []
    assert fake.uploads == []


def test_saved_project_generation_uses_project_identity_authority() -> None:
    source = read_contract_text("app_modules/saved_project_generation.py")

    assert "ensure_active_project_id" in source
    assert "project_id=project_id" in source


def test_repository_lists_downloads_and_deletes_project_files() -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    fake.rest_get = lambda table, params: (
        [{"storage_path": "itineraries/itinerary-id/calculator/test.xlsx"}]
        if table == "itinerary_files"
        else []
    )
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )

    assert repository.download_file("itineraries/itinerary-id/calculator/test.xlsx") == b"downloaded"
    result = repository.delete_itinerary("itinerary-id")

    assert result.ok is True
    assert result.complete is True
    assert result.storage_paths == ("itineraries/itinerary-id/calculator/test.xlsx",)
    assert fake.downloads == [("itinerary-files", "itineraries/itinerary-id/calculator/test.xlsx")]
    assert fake.rest_deletes == [("itineraries", {"id": "eq.itinerary-id"})]
    assert fake.storage_deletes == [("itinerary-files", ["itineraries/itinerary-id/calculator/test.xlsx"])]


def test_project_browser_supports_paging_search_delete_and_lazy_file_downloads() -> None:
    storage_source = read_contract_text("project_storage/project_browser.py")
    service_source = read_contract_text("app_modules/project_storage_service.py")
    ui_source = read_contract_text("app_modules/project_browser_ui.py")
    controls_source = read_contract_text("app_modules/project_browser_controls.py")
    detail_source = read_contract_text("app_modules/project_browser_detail_ui.py")
    calculator_file_source = read_contract_text("app_modules/project_browser_calculation_files.py")

    assert "search: str = """ in storage_source
    assert "get_project_storage_repository" not in storage_source
    assert "list_cloud_itinerary_page" in service_source
    assert "list_cloud_project_explorer_page" in service_source
    assert "offset=clean_page * clean_size" in service_source
    assert "list_cloud_calculation_files" in service_source
    assert "download_cloud_project_file" in service_source
    assert "delete_cloud_itinerary_result" in service_source
    assert "Search" in controls_source
    assert "Manage multiple projects" not in controls_source
    assert "Trash" not in controls_source
    assert "Move to Trash" not in detail_source
    assert "Delete" in detail_source
    assert "Delete" in detail_source
    assert "Delete permanently" not in detail_source
    assert "render_calculation_files(project_id)" in detail_source
    assert "Calculator files" in calculator_file_source



def test_repository_delete_retains_record_when_storage_cleanup_fails() -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    fake.rest_get = lambda table, params: (
        [{"storage_path": "itineraries/itinerary-id/exports/test.pdf"}]
        if table == "itinerary_files"
        else []
    )
    fake.fail_storage_delete = RuntimeError("storage cleanup failed")
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )

    result = repository.delete_itinerary("itinerary-id")

    assert result.ok is False
    assert result.complete is False
    assert result.record_deleted is False
    assert result.storage_files_deleted is False
    assert "storage cleanup failed" in result.storage_error
    assert fake.rest_deletes == []
    assert fake.storage_deletes == []

def test_first_snapshot_save_removes_new_project_row_when_version_insert_fails(monkeypatch) -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    fake.fail_create_version = RuntimeError("raw service key should not reach the UI")
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )
    monkeypatch.setattr("app_modules.project_storage_workflow.get_project_storage_repository", lambda: repository)
    app_state = {"active_project_storage_id": "11111111-2222-3333-4444-555555555555"}

    ok = save_project_payload_snapshot(
        app_state,
        {"metadata": {"itinerary_name": "Norway Winter"}, "output_brand": "agent"},
    )

    assert ok is False
    assert fake.uploads == []
    assert ("itineraries", {"id": "eq.11111111-2222-3333-4444-555555555555"}) in fake.rest_deletes
    assert app_state["project_storage_last_error"] == "Project was not saved to Supabase. Try again before closing this session."
    assert "raw service key" in app_state["project_storage_last_error_detail"]


def test_existing_snapshot_save_removes_new_version_when_metadata_update_fails(monkeypatch) -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    fake.fail_itinerary_upsert = RuntimeError("metadata update failed")
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )
    monkeypatch.setattr("app_modules.project_storage_workflow.get_project_storage_repository", lambda: repository)
    app_state = {
        "active_project_storage_id": "11111111-2222-3333-4444-555555555555",
        "active_project_cloud_persisted": True,
    }

    ok = save_project_payload_snapshot(
        app_state,
        {"metadata": {"itinerary_name": "Norway Winter"}, "output_brand": "agent"},
    )

    assert ok is False
    assert fake.uploads == []
    assert ("itinerary_versions", {"id": "eq.itinerary_versions-id"}) in fake.rest_deletes
    assert app_state["project_storage_last_error"] == "Project was not saved to Supabase. Try again before closing this session."
