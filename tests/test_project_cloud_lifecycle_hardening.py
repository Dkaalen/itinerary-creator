from __future__ import annotations

from project_storage.repository import ProjectStorageRepository


class RecordingProjectRepository:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.created_versions: list[dict] = []
        self.deleted_projects: list[str] = []

    def upsert_itinerary(self, itinerary_id: str, *, name: str, status: str = "draft"):
        self.upserts.append({"itinerary_id": itinerary_id, "name": name, "status": status})
        return {"id": itinerary_id, "name": name}

    def create_itinerary(self, itinerary_id: str, *, name: str, status: str = "draft"):
        return self.upsert_itinerary(itinerary_id, name=name, status=status)

    def next_version_number(self, itinerary_id: str, itinerary_type: str) -> int:
        return 7

    def create_version(self, **payload):
        self.created_versions.append(payload)
        return {"id": "version-id"}

    def delete_itinerary(self, itinerary_id: str):  # pragma: no cover - rollback only
        self.deleted_projects.append(itinerary_id)

    def delete_version(self, version_id: str) -> None:  # pragma: no cover - rollback only
        raise AssertionError(f"unexpected rollback: {version_id}")


def test_manual_cloud_save_normalizes_payload_project_id_to_active_storage_id(monkeypatch) -> None:
    from app_modules import project_storage_workflow as workflow_hooks

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
    assert saved_payload["metadata"]["project_id"] == "cloud-row-id"
    assert state["active_saved_project"]["metadata"]["project_id"] == "cloud-row-id"
    assert state["active_project_cloud_persisted"] is True
    assert state["project_storage_last_saved_version_id"] == "version-id"
    assert state["project_storage_last_saved_baseline"]["metadata"]["project_id"] == "cloud-row-id"
    assert repository.deleted_projects == []
    assert repository.upserts == [{"itinerary_id": "cloud-row-id", "name": "Norway Cloud Trip", "status": "draft"}]


def test_repository_delete_file_removes_storage_before_db_record() -> None:
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
        ("bucket:project-files", ("itineraries/trip/calculator.xlsx",)),
        ("itinerary_files", {"id": "eq.file-id"}),
    ]


def test_repository_delete_file_retains_record_when_storage_cleanup_fails() -> None:
    calls: list[tuple[str, object]] = []

    class Client:
        def rest_delete(self, table, filters):
            calls.append((table, filters))

        def storage_delete(self, bucket, paths):
            raise RuntimeError("storage down")

    config = type("Config", (), {"bucket": "project-files"})()
    repository = ProjectStorageRepository(config, client=Client())

    result = repository.delete_file("file-id", storage_path="itineraries/trip/calculator.xlsx")

    assert result.ok is False
    assert result.complete is False
    assert result.record_deleted is False
    assert result.storage_files_deleted is False
    assert "storage down" in result.storage_error
    assert calls == []


def test_cloud_open_marks_normalized_loaded_payload_as_saved_baseline(monkeypatch) -> None:
    from types import SimpleNamespace
    from tests.support.streamlit_stub import SessionState, install_streamlit_stub
    from app_modules import project_browser_actions

    st = install_streamlit_stub(force=True)
    state = SessionState()
    st.session_state = state
    project_browser_actions.st.session_state = state
    raw_payload = {
        "metadata": {"project_id": "stale-id", "itinerary_name": "Cloud trip"},
        "current_snapshot": {"parsed_rows": [], "output_edits": {}},
    }

    monkeypatch.setattr(project_browser_actions, "load_latest_cloud_project_payload", lambda project_id: raw_payload)

    def load(session, payload, *, project_id_override):
        session["active_saved_project"] = {
            **payload,
            "metadata": {**payload["metadata"], "project_id": project_id_override},
        }
        return SimpleNamespace(ok=True, message="Opened")

    monkeypatch.setattr(project_browser_actions, "load_saved_project", load)
    monkeypatch.setattr(project_browser_actions, "prepare_project_switch", lambda session: None)
    monkeypatch.setattr(project_browser_actions.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(project_browser_actions.st, "rerun", lambda: None)

    project_browser_actions.open_cloud_project("cloud-id")

    assert state["project_storage_last_saved_baseline"]["metadata"]["project_id"] == "cloud-id"
    assert state["active_project_cloud_persisted"] is True
