from __future__ import annotations

from pathlib import Path

from calculator.calculator_state import CalculatorState
from project_storage.config import supabase_config_from_mapping
from project_storage.paths import calculator_workbook_path, itinerary_snapshot_path, pdf_export_path, safe_segment
from project_storage.repository import ProjectStorageRepository
from project_storage.workflow_hooks import ensure_storage_itinerary, save_calculation_workbook


class FakeClient:
    def __init__(self) -> None:
        self.rest_inserts = []
        self.rest_gets = []
        self.uploads = []

    def rest_insert(self, table, payload, *, upsert=False):
        self.rest_inserts.append((table, payload, upsert))
        row = {**payload}
        row.setdefault("id", f"{table}-id")
        return [row]

    def rest_get(self, table, params):
        self.rest_gets.append((table, params))
        return [{"version_number": 3}]

    def storage_upload(self, bucket, storage_path, content, *, content_type):
        self.uploads.append((bucket, storage_path, content, content_type))


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

    assert fake.rest_inserts[0] == (
        "itineraries",
        {"id": "itinerary-id", "name": "Norway Winter", "status": "draft"},
        True,
    )
    assert fake.uploads[0][0] == "itinerary-files"
    assert fake.rest_inserts[-1][0] == "itinerary_files"


def test_workflow_hook_reuses_existing_itinerary_id(monkeypatch) -> None:
    from project_storage.config import SupabaseStorageConfig

    fake = FakeClient()
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="sb_secret", bucket="itinerary-files"),
        client=fake,
    )
    monkeypatch.setattr("project_storage.workflow_hooks.get_project_storage_repository", lambda: repository)
    app_state = {"active_project_storage_id": "11111111-2222-3333-4444-555555555555"}
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


def test_saved_project_generation_reuses_storage_id() -> None:
    source = Path("app_modules/saved_project_generation.py").read_text(encoding="utf-8")

    assert "active_project_storage_id" in source
    assert "project_id=project_id" in source
