from __future__ import annotations

import http.client

import pytest

from app_modules import project_storage_service
from project_storage.capabilities import ProjectStorageCapabilities
from project_storage.config import SupabaseStorageConfig
from project_storage.http_client import SupabaseRequestError
from project_storage.http_transport import PersistentHttpTransport
from project_storage.repository import ProjectStorageRepository


class CapabilityClient:
    def __init__(self, *, schema_status: int | None = None, folder_status: int | None = None) -> None:
        self.schema_status = schema_status
        self.folder_status = folder_status
        self.gets = 0
        self.rpcs = 0

    def rest_get(self, table, params):
        self.gets += 1
        if self.schema_status is not None:
            raise SupabaseRequestError("schema unavailable", status=self.schema_status)
        return []

    def rest_rpc(self, function_name, payload):
        self.rpcs += 1
        if self.folder_status is not None:
            raise SupabaseRequestError("folder rpc unavailable", status=self.folder_status)
        return []


def _repository(client: object) -> ProjectStorageRepository:
    return ProjectStorageRepository(
        SupabaseStorageConfig(
            url="https://example.supabase.co",
            secret_key="secret",
            bucket="project-files",
        ),
        client=client,
    )


def test_capability_check_is_cached_and_reuses_the_folder_query_result() -> None:
    client = CapabilityClient()
    repository = _repository(client)

    first = repository.project_management_capabilities()
    second = repository.project_management_capabilities()
    folders = repository.list_project_folders()

    assert first == ProjectStorageCapabilities.full()
    assert second is first
    assert folders == ()
    assert client.gets == 1
    assert client.rpcs == 1


def test_missing_management_schema_skips_folder_rpc_and_is_cached() -> None:
    client = CapabilityClient(schema_status=400)
    repository = _repository(client)

    assert repository.project_management_capabilities() == ProjectStorageCapabilities.legacy()
    assert repository.project_management_capabilities() == ProjectStorageCapabilities.legacy()
    assert client.gets == 1
    assert client.rpcs == 0


def test_missing_folder_rpc_keeps_owner_management_without_folder_controls() -> None:
    client = CapabilityClient(folder_status=404)
    repository = _repository(client)

    capabilities = repository.project_management_capabilities()

    assert capabilities.management_schema is True
    assert capabilities.organization_controls is True
    assert capabilities.folder_filter is False
    assert client.gets == 1
    assert client.rpcs == 1


def test_transient_capability_failure_is_not_cached_as_missing_schema() -> None:
    client = CapabilityClient(schema_status=503)
    repository = _repository(client)

    with pytest.raises(SupabaseRequestError):
        repository.project_management_capabilities()
    with pytest.raises(SupabaseRequestError):
        repository.project_management_capabilities()

    assert client.gets == 2
    assert client.rpcs == 0


def test_explorer_service_uses_only_active_management_query_arguments(monkeypatch) -> None:
    captured: list[dict] = []

    def management_page(repository, **kwargs):
        captured.append(kwargs)
        from project_storage.project_results import ProjectListResult

        return ProjectListResult(projects=(), total_count=0)

    monkeypatch.setattr(project_storage_service, "get_project_storage_repository", lambda: object())
    monkeypatch.setattr(project_storage_service, "list_project_management_page", management_page)

    project_storage_service.list_cloud_project_explorer_page(
        page_index=2,
        page_size=25,
        search="Norway",
        sort="name",
        owner_slug="Dennis",
        folder_name="ITIN-2020",
    )

    assert captured == [{
        "limit": 25,
        "offset": 50,
        "search": "Norway",
        "sort": "name",
        "owner_slug": "Dennis",
        "folder_name": "ITIN-2020",
    }]


def test_project_page_cache_reuses_exact_count_and_mutation_invalidates_it() -> None:
    class Client:
        def __init__(self) -> None:
            self.count_gets = 0
            self.updates = 0

        def rest_get_with_count(self, table, params):
            self.count_gets += 1
            return ([{"id": "project-1"}], 1)

        def rest_update(self, table, params, payload):
            self.updates += 1
            return [{"id": "project-1"}]

    client = Client()
    repository = _repository(client)

    repository.list_project_page()
    repository.list_project_page()
    repository.bulk_update_project_organization(
        ["project-1"], owner_slug="Dennis", actor_slug="Dennis"
    )
    repository.list_project_page()

    assert client.count_gets == 2
    assert client.updates == 1


def test_persistent_transport_reuses_one_https_connection(monkeypatch) -> None:
    created: list[FakeConnection] = []

    def factory(*args, **kwargs):
        connection = FakeConnection()
        created.append(connection)
        return connection

    monkeypatch.setattr("project_storage.http_transport.http.client.HTTPSConnection", factory)
    transport = PersistentHttpTransport("https://example.supabase.co", timeout=4)

    first = transport.request("GET", "/rest/v1/itineraries", data=None, headers={})
    second = transport.request("GET", "/rest/v1/itineraries?limit=1", data=None, headers={})
    transport.close()

    assert first.status == second.status == 200
    assert len(created) == 1
    assert [call[1] for call in created[0].calls] == [
        "/rest/v1/itineraries",
        "/rest/v1/itineraries?limit=1",
    ]
    assert created[0].closed is True


def test_persistent_transport_reconnects_once_after_stale_connection(monkeypatch) -> None:
    created: list[FakeConnection] = []

    def factory(*args, **kwargs):
        connection = FakeConnection(fail_request=not created)
        created.append(connection)
        return connection

    monkeypatch.setattr("project_storage.http_transport.http.client.HTTPSConnection", factory)
    transport = PersistentHttpTransport("https://example.supabase.co")

    response = transport.request("GET", "/rest/v1/itineraries", data=None, headers={})

    assert response.status == 200
    assert len(created) == 2
    assert created[0].closed is True


class FakeResponse:
    status = 200
    will_close = False

    def read(self):
        return b"[]"

    def getheaders(self):
        return [("content-type", "application/json")]


class FakeConnection:
    def __init__(self, *, fail_request: bool = False) -> None:
        self.fail_request = fail_request
        self.calls: list[tuple[str, str, object, dict]] = []
        self.closed = False

    def request(self, method, path, body=None, headers=None):
        if self.fail_request:
            self.fail_request = False
            raise http.client.RemoteDisconnected("stale")
        self.calls.append((method, path, body, dict(headers or {})))

    def getresponse(self):
        return FakeResponse()

    def close(self):
        self.closed = True


def test_storage_failure_in_second_batch_retains_only_its_project() -> None:
    class Client:
        def __init__(self) -> None:
            self.storage_calls = 0
            self.deleted_filters: list[str] = []

        def rest_get(self, table, params):
            expression = str(params.get("id") or params.get("itinerary_id") or "")
            if expression.startswith("eq."):
                ids = [expression.removeprefix("eq.")]
            else:
                ids = expression.removeprefix("in.(").removesuffix(")").split(",")
            ids = [value for value in ids if value]
            if table == "itineraries":
                return [{"id": value} for value in ids]
            return [
                {
                    "id": f"file-{value}",
                    "itinerary_id": value,
                    "storage_path": f"itineraries/{value}/file.pdf",
                }
                for value in ids
            ]

        def storage_delete(self, bucket, paths):
            self.storage_calls += 1
            if self.storage_calls == 2:
                raise RuntimeError("second storage batch failed")

        def rest_delete(self, table, params):
            self.deleted_filters.append(params["id"])
            expression = str(params["id"])
            if expression.startswith("eq."):
                ids = [expression.removeprefix("eq.")]
            else:
                ids = expression.removeprefix("in.(").removesuffix(")").split(",")
            return [{"id": value} for value in ids if value]

    project_ids = tuple(f"project-{index:03d}" for index in range(101))
    repository = _repository(Client())

    result = repository.permanently_delete_itineraries(project_ids)

    assert len(result.deleted_ids) == 100
    assert result.incomplete_ids == ("project-100",)
    assert result.items[-1].result.storage_files_deleted is False


def test_database_batch_failure_keeps_cleaned_records_retryable() -> None:
    class Client:
        def rest_get(self, table, params):
            expression = str(params.get("id") or params.get("itinerary_id") or "")
            ids = expression.removeprefix("in.(").removesuffix(")").split(",")
            ids = [value for value in ids if value]
            if table == "itineraries":
                return [{"id": value} for value in ids]
            return []

        def storage_delete(self, bucket, paths):
            raise AssertionError("projects have no files")

        def rest_delete(self, table, params):
            raise RuntimeError("database unavailable")

    repository = _repository(Client())

    result = repository.permanently_delete_itineraries(("project-1", "project-2"))

    assert result.deleted_ids == ()
    assert result.incomplete_ids == ("project-1", "project-2")
    assert all(item.result.storage_files_deleted for item in result.items)
    assert all("database unavailable" in item.result.record_error for item in result.items)


def test_unsupported_controls_are_removed_from_legacy_sort_options() -> None:
    from app_modules.project_browser_controls import _sort_options

    legacy = _sort_options(ProjectStorageCapabilities.legacy())
    management = _sort_options(ProjectStorageCapabilities.management_only())
    full = _sort_options(ProjectStorageCapabilities.full())

    assert "owner" not in legacy
    assert "folder" not in legacy
    assert "owner" in management
    assert "folder" not in management
    assert "owner" in full
    assert "folder" in full


def test_bulk_management_actions_follow_detected_schema_capabilities() -> None:
    from app_modules.project_browser_bulk_ui import _bulk_action_options
    from app_modules.project_browser_controls import ProjectBrowserQuery

    legacy_query = ProjectBrowserQuery(organization_available=False)
    management_query = ProjectBrowserQuery(organization_available=True)

    assert _bulk_action_options(legacy_query) == ("delete",)
    assert _bulk_action_options(management_query) == ("owner", "folder", "delete")


def test_folder_options_are_scoped_to_the_current_owner(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_controls
    from project_storage.project_results import ProjectFolderOption
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        project_browser_controls,
        "list_cloud_project_folders",
        lambda **kwargs: calls.append(kwargs)
        or (ProjectFolderOption(folder_name="VIP-2026", project_count=2),),
    )

    folders = project_browser_controls._folder_options(
        ProjectStorageCapabilities.full(),
        owner_slug="vipin",
    )

    assert folders == ("VIP-2026",)
    assert calls == [{"owner_slug": "vipin"}]


def test_invalid_legacy_folder_row_does_not_disable_folder_capability() -> None:
    class Client(CapabilityClient):
        def rest_rpc(self, function_name, payload):
            self.rpcs += 1
            return [
                {"folder_name": "Valid folder", "project_count": 2},
                {"folder_name": "invalid/folder", "project_count": 1},
            ]

    client = Client()
    repository = _repository(client)

    capabilities = repository.project_management_capabilities()
    folders = repository.list_project_folders()

    assert capabilities == ProjectStorageCapabilities.full()
    assert tuple(item.folder_name for item in folders) == ("Valid folder",)


def test_persistent_transport_applies_the_configured_timeout(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def factory(*args, **kwargs):
        captured.append(dict(kwargs))
        return FakeConnection()

    monkeypatch.setattr("project_storage.http_transport.http.client.HTTPSConnection", factory)
    transport = PersistentHttpTransport("https://example.supabase.co", timeout=7.5)

    transport.request("GET", "/rest/v1/itineraries", data=None, headers={})

    assert len(captured) == 1
    assert captured[0]["timeout"] == 7.5
    assert captured[0]["context"] is not None
