from __future__ import annotations

from project_storage.repository import ProjectStorageRepository


class RecordingProjectRepository:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.created_versions: list[dict] = []
        self.registered_files: list[dict] = []
        self.uploads: list[tuple[str, bytes]] = []

    def upsert_itinerary(self, itinerary_id: str, *, name: str, status: str = "draft"):
        self.upserts.append({"itinerary_id": itinerary_id, "name": name, "status": status})
        return {"id": itinerary_id, "name": name}

    def next_version_number(self, itinerary_id: str, itinerary_type: str) -> int:
        return 7

    def upload_file(self, storage_path: str, content: bytes, *, content_type: str) -> None:
        self.uploads.append((storage_path, content))

    def create_version(self, **payload):
        self.created_versions.append(payload)
        return {"id": "version-id"}

    def register_file(self, **payload):
        self.registered_files.append(payload)
        return {"id": "file-id"}

    def delete_storage_files(self, storage_paths: list[str]) -> None:  # pragma: no cover - rollback only
        raise AssertionError(f"unexpected rollback: {storage_paths}")

    def delete_version(self, version_id: str) -> None:  # pragma: no cover - rollback only
        raise AssertionError(f"unexpected rollback: {version_id}")


def test_manual_cloud_save_normalizes_payload_project_id_to_active_storage_id(monkeypatch) -> None:
    from project_storage import workflow_hooks

    repository = RecordingProjectRepository()
    monkeypatch.setattr(workflow_hooks, "get_project_storage_repository", lambda: repository)
    state = {
        "active_project_storage_id": "cloud-row-id",
        "active_saved_project_id": "cloud-row-id",
        "itinerary_name": "Norway Cloud Trip",
    }
    payload = {
        "metadata": {"project_id": "stale-backup-id", "itinerary_name": "Norway Cloud Trip", "status": "draft"},
        "output_brand": "agent",
        "mode": "agent",
        "current_snapshot": {"output_edits": {}},
    }

    assert workflow_hooks.save_project_payload_snapshot(state, payload, source_type="manual_save") is True

    saved_payload = repository.created_versions[0]["payload"]
    uploaded_payload = repository.uploads[0][1].decode("utf-8")
    assert saved_payload["metadata"]["project_id"] == "cloud-row-id"
    assert '"project_id": "cloud-row-id"' in uploaded_payload
    assert state["active_saved_project"]["metadata"]["project_id"] == "cloud-row-id"
    assert state["project_storage_last_saved_snapshot_path"].endswith("agent-v007.json")
    assert repository.upserts == [{"itinerary_id": "cloud-row-id", "name": "Norway Cloud Trip", "status": "draft"}]


def test_repository_delete_file_deletes_db_record_then_storage_object() -> None:
    calls: list[tuple[str, object]] = []

    class Client:
        def rest_delete(self, table, filters):
            calls.append((table, filters))

        def storage_delete(self, bucket, paths):
            calls.append((f"bucket:{bucket}", tuple(paths)))

    config = type("Config", (), {"bucket": "project-files"})()
    repository = ProjectStorageRepository(config, client=Client())

    result = repository.delete_file("file-id", storage_path="itineraries/trip/calculator.xlsx")

    assert result.ok is True
    assert result.complete is True
    assert calls == [
        ("itinerary_files", {"id": "eq.file-id"}),
        ("bucket:project-files", ("itineraries/trip/calculator.xlsx",)),
    ]


def test_repository_delete_file_reports_partial_storage_cleanup_failure() -> None:
    calls: list[tuple[str, object]] = []

    class Client:
        def rest_delete(self, table, filters):
            calls.append((table, filters))

        def storage_delete(self, bucket, paths):
            raise RuntimeError("storage down")

    config = type("Config", (), {"bucket": "project-files"})()
    repository = ProjectStorageRepository(config, client=Client())

    result = repository.delete_file("file-id", storage_path="itineraries/trip/calculator.xlsx")

    assert result.ok is True
    assert result.complete is False
    assert result.storage_files_deleted is False
    assert "storage down" in result.storage_error
    assert calls == [("itinerary_files", {"id": "eq.file-id"})]
