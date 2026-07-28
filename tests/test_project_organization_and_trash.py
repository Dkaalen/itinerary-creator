from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_storage.config import SupabaseStorageConfig
from project_storage.delete_result import ProjectDeleteResult
from project_storage.http_client import SupabaseHttpClient
from project_storage.http_transport import HttpTransportResponse
from project_storage.project_metadata import (
    PROJECT_OWNER_SLUGS,
    ProjectOrganization,
    normalize_project_folder,
    normalize_project_owner,
    project_owner_label,
)
from project_storage.repository import ProjectStorageRepository
from project_storage.version_writer import save_project_version


class ManagementClient:
    def __init__(
        self,
        *,
        files: list[dict] | None = None,
        trashed_ids: set[str] | None = None,
        update_failures: set[int] | None = None,
    ) -> None:
        self.count_gets: list[tuple[str, dict[str, str]]] = []
        self.gets: list[tuple[str, dict[str, str]]] = []
        self.updates: list[tuple[str, dict[str, str], dict]] = []
        self.deletes: list[tuple[str, dict[str, str]]] = []
        self.storage_deletes: list[tuple[str, tuple[str, ...]]] = []
        self.rpc_calls: list[tuple[str, dict]] = []
        self.files = list(files or [])
        self.trashed_ids = set(trashed_ids or set())
        self.update_failures = set(update_failures or set())

    def rest_get_with_count(self, table, params):
        self.count_gets.append((table, dict(params)))
        return ([{"id": "project-1", "name": "Norway"}], 47)

    def rest_get(self, table, params):
        self.gets.append((table, dict(params)))
        if table == "itinerary_files":
            offset = int(params.get("offset", 0))
            limit = int(params.get("limit", 500))
            expression = str(params.get("itinerary_id") or "")
            project_ids = (
                expression.removeprefix("in.(").removesuffix(")").split(",")
                if expression.startswith("in.(")
                else [expression.removeprefix("eq.")]
            )
            rows = []
            for item in self.files:
                project_id = str(item.get("itinerary_id") or (project_ids[0] if len(project_ids) == 1 else ""))
                if project_id in project_ids:
                    rows.append({**item, "itinerary_id": project_id})
            return rows[offset : offset + limit]
        if table == "itineraries":
            expression = str(params.get("id") or "")
            if expression.startswith("in.("):
                project_ids = expression.removeprefix("in.(").removesuffix(")").split(",")
                return [
                    {
                        "id": project_id,
                        "deleted_at": "2026-07-27T19:00:00Z" if project_id in self.trashed_ids else None,
                    }
                    for project_id in project_ids
                    if project_id
                ]
            project_id = expression.removeprefix("eq.")
            return [{"id": project_id, "owner_slug": "dennis", "folder_name": "ITIN-2020"}]
        return []

    def rest_rpc(self, function_name, payload):
        self.rpc_calls.append((function_name, dict(payload)))
        return [
            {"folder_name": "ITIN-2020", "project_count": 3},
            {"folder_name": "Iceland Winter", "project_count": "2"},
            {"folder_name": "", "project_count": 9},
        ]

    def rest_update(self, table, params, payload):
        call_index = len(self.updates)
        self.updates.append((table, dict(params), dict(payload)))
        if call_index in self.update_failures:
            raise RuntimeError(f"update batch {call_index + 1} failed")
        expression = str(params["id"])
        values = expression.removeprefix("in.(").removesuffix(")")
        return [{"id": value} for value in values.split(",") if value]

    def rest_delete(self, table, params):
        self.deletes.append((table, dict(params)))
        return []

    def storage_delete(self, bucket, paths):
        self.storage_deletes.append((bucket, tuple(paths)))


def _repository(client: object) -> ProjectStorageRepository:
    return ProjectStorageRepository(
        SupabaseStorageConfig(
            url="https://example.supabase.co",
            secret_key="secret",
            bucket="itinerary-files",
        ),
        client=client,
    )


def test_project_owner_and_folder_metadata_are_bounded_and_normalized() -> None:
    assert PROJECT_OWNER_SLUGS == ("unassigned", "dennis", "vipin", "christer", "shared")
    assert normalize_project_owner(" Dennis ") == "dennis"
    assert normalize_project_owner("") == "unassigned"
    assert project_owner_label("christer") == "Christer"
    assert normalize_project_folder("  ITIN-2020   Winter ") == "ITIN-2020 Winter"
    assert ProjectOrganization.from_values(
        owner_slug="Vipin",
        folder_name="ITIN-2042",
        actor_slug="Vipin",
    ) == ProjectOrganization(owner_slug="vipin", folder_name="ITIN-2042", actor_slug="vipin")

    with pytest.raises(ValueError, match="Project owner"):
        normalize_project_owner("someone-else")
    with pytest.raises(ValueError, match="slash"):
        normalize_project_folder("Dennis/ITIN-2020")
    with pytest.raises(ValueError, match="80"):
        normalize_project_folder("x" * 81)
    with pytest.raises(ValueError, match="letters, numbers"):
        normalize_project_folder("ITIN-2020,(draft)")


def test_legacy_project_save_payload_does_not_require_additive_schema_columns() -> None:
    class Client:
        def __init__(self) -> None:
            self.inserts: list[tuple[str, dict, bool]] = []

        def rest_insert(self, table, payload, *, upsert=False):
            self.inserts.append((table, dict(payload), bool(upsert)))
            return [dict(payload)]

    client = Client()
    repository = _repository(client)

    repository.create_itinerary("project-1", name="Norway")
    repository.upsert_itinerary("project-1", name="Norway updated")

    assert "last_saved_at" not in client.inserts[0][1]
    assert "last_saved_at" not in client.inserts[1][1]
    assert client.inserts[0][2] is False
    assert client.inserts[1][2] is True


def test_version_writer_propagates_explicit_project_organization_to_metadata_row() -> None:
    calls: list[tuple[str, dict]] = []

    class Repository:
        def next_version_number(self, itinerary_id, itinerary_type):
            return 1

        def create_itinerary(self, itinerary_id, *, name, status, **kwargs):
            calls.append(("create", {"id": itinerary_id, "name": name, "status": status, **kwargs}))
            return {"id": itinerary_id}

        def create_version(self, **kwargs):
            calls.append(("version", kwargs))
            return {"id": "version-1"}

        def delete_itinerary(self, itinerary_id):
            raise AssertionError(f"unexpected rollback for {itinerary_id}")

    payload = {
        "metadata": {
            "owner_slug": "Dennis",
            "folder_name": "ITIN-2020",
            "created_by": "Dennis",
            "updated_by": "Vipin",
        }
    }

    result = save_project_version(
        Repository(),
        itinerary_id="project-1",
        name="Norway",
        status="draft",
        itinerary_type="agent",
        source_type="manual_save",
        payload=payload,
        project_already_persisted=False,
    )

    assert result.version_id == "version-1"
    organization = calls[0][1]["organization"]
    assert organization == ProjectOrganization(
        owner_slug="dennis",
        folder_name="ITIN-2020",
        actor_slug="vipin",
    )


def test_additive_supabase_migration_defines_organization_revision_and_trash_contract() -> None:
    migration = Path("supabase/migrations/20260727190000_project_organization_and_trash.sql").read_text(
        encoding="utf-8"
    ).casefold()

    for column in (
        "owner_slug",
        "folder_name",
        "created_by",
        "updated_by",
        "revision",
        "last_saved_at",
        "deleted_at",
        "deleted_by",
    ):
        assert f"add column if not exists {column}" in migration
    assert "itineraries_active_owner_recent_idx" in migration
    assert "itineraries_active_folder_recent_idx" in migration
    assert "itineraries_trash_recent_idx" in migration
    assert "create or replace function public.list_project_folders" in migration
    assert "create or replace function public.sync_itinerary_last_saved_at" in migration
    assert "after insert or delete on public.itinerary_versions" in migration
    assert "grant execute on function public.list_project_folders" in migration
    assert "drop table" not in migration
    assert "truncate" not in migration


def test_counted_http_reads_parse_postgrest_content_range(monkeypatch) -> None:
    client = SupabaseHttpClient(
        SupabaseStorageConfig(url="https://example.supabase.co", secret_key="secret", bucket="files")
    )
    calls: list[tuple[str, str, dict[str, str]]] = []

    def response(method, path, *, data=None, headers=None):
        calls.append((method, path, dict(headers or {})))
        return json.dumps([{"id": "project-1"}]).encode(), {"content-range": "25-25/47"}

    monkeypatch.setattr(client, "_request_with_headers", response)

    rows, total = client.rest_get_with_count("itineraries", {"limit": "1", "offset": "25"})

    assert rows == [{"id": "project-1"}]
    assert total == 47
    assert calls[0][0] == "GET"
    assert calls[0][2]["Prefer"] == "count=exact"


def test_http_observer_reports_safe_endpoint_without_query_values() -> None:
    events: list[dict] = []

    class Transport:
        def request(self, method, path, *, data, headers):
            assert "Private+Client+Name" in path
            assert headers["apikey"] == "secret"
            return HttpTransportResponse(
                status=200,
                headers={"content-type": "application/json"},
                body=b'[{"id":"project-1"}]',
            )

        def close(self):
            return None

    client = SupabaseHttpClient(
        SupabaseStorageConfig(url="https://example.supabase.co", secret_key="secret", bucket="files"),
        observer=lambda event: events.append(dict(event)),
        transport=Transport(),
    )

    rows = client.rest_get("itineraries", {"name": "eq.Private Client Name"})

    assert rows == [{"id": "project-1"}]
    assert len(events) == 1
    assert events[0]["endpoint"] == "rest:itineraries"
    assert events[0]["method"] == "GET"
    assert events[0]["ok"] is True
    assert events[0]["status"] == 200
    assert "Private Client Name" not in str(events[0])
    assert "secret" not in str(events[0]).casefold()


def test_http_rpc_calls_only_the_named_postgrest_function(monkeypatch) -> None:
    client = SupabaseHttpClient(
        SupabaseStorageConfig(url="https://example.supabase.co", secret_key="secret", bucket="files")
    )
    calls: list[tuple[str, str, dict, str]] = []

    def json_request(method, path, *, payload=None, prefer=None):
        calls.append((method, path, dict(payload or {}), str(prefer or "")))
        return [{"folder_name": "ITIN-2020", "project_count": 2}]

    monkeypatch.setattr(client, "_json_request", json_request)

    rows = client.rest_rpc("list_project_folders", {"p_owner_slug": "dennis"})

    assert rows == [{"folder_name": "ITIN-2020", "project_count": 2}]
    assert calls == [
        (
            "POST",
            "/rest/v1/rpc/list_project_folders",
            {"p_owner_slug": "dennis"},
            "return=representation",
        )
    ]

    with pytest.raises(ValueError, match="function name"):
        client.rest_rpc("", {})


def test_http_patch_uses_explicit_filters_and_returns_rows(monkeypatch) -> None:
    client = SupabaseHttpClient(
        SupabaseStorageConfig(url="https://example.supabase.co", secret_key="secret", bucket="files")
    )
    calls: list[tuple[str, str, dict, str]] = []

    def json_request(method, path, *, payload=None, prefer=None):
        calls.append((method, path, dict(payload or {}), str(prefer or "")))
        return [{"id": "project-1"}]

    monkeypatch.setattr(client, "_json_request", json_request)

    rows = client.rest_update(
        "itineraries",
        {"id": "eq.project-1"},
        {"folder_name": "ITIN-2020"},
    )

    assert rows == [{"id": "project-1"}]
    assert calls == [
        (
            "PATCH",
            "/rest/v1/itineraries?id=eq.project-1",
            {"folder_name": "ITIN-2020"},
            "return=representation",
        )
    ]


def test_management_page_has_exact_count_filters_and_stable_ordering() -> None:
    client = ManagementClient()
    repository = _repository(client)

    result = repository.list_project_page(
        limit=25,
        offset=25,
        search="Norway 2027",
        sort="owner",
        owner_slug="Dennis",
        folder_name="ITIN-2020",
    )

    assert result.projects == ({"id": "project-1", "name": "Norway"},)
    assert result.total_count == 47
    table, params = client.count_gets[0]
    assert table == "itineraries"
    assert params["owner_slug"] == "eq.dennis"
    assert params["folder_name"] == "eq.ITIN-2020"
    assert params["deleted_at"] == "is.null"
    assert params["order"] == "owner_slug.asc,last_saved_at.desc,id.asc"
    assert params["offset"] == "25"
    assert "name.ilike.*Norway 2027*" in params["or"]
    assert "folder_name.ilike.*Norway 2027*" in params["or"]


def test_folder_options_are_server_owned_counted_and_owner_filtered() -> None:
    client = ManagementClient()
    repository = _repository(client)

    options = repository.list_project_folders(owner_slug="Dennis")

    assert [(option.folder_name, option.project_count) for option in options] == [
        ("ITIN-2020", 3),
        ("Iceland Winter", 2),
    ]
    assert client.rpc_calls == [
        (
            "list_project_folders",
            {"p_owner_slug": "dennis", "p_include_trashed": False},
        )
    ]


def test_management_search_strips_postgrest_filter_grammar() -> None:
    client = ManagementClient()
    repository = _repository(client)

    repository.list_project_page(search="Norway),deleted_at.not.is.null")

    params = client.count_gets[0][1]
    assert params["deleted_at"] == "is.null"
    assert ")" not in params["or"].replace("(name.ilike.", "", 1).rsplit(")", 1)[0]
    assert ",deleted_at." not in params["or"]


def test_management_query_always_excludes_soft_deleted_rows() -> None:
    client = ManagementClient()
    repository = _repository(client)

    repository.list_project_page(sort="recent")

    params = client.count_gets[0][1]
    assert params["deleted_at"] == "is.null"
    assert params["order"] == "last_saved_at.desc,id.asc"


def test_bulk_organization_deduplicates_ids_and_batches_large_mutations() -> None:
    client = ManagementClient()
    repository = _repository(client)
    project_ids = [f"project-{index}" for index in range(205)] + ["project-7"]

    result = repository.bulk_update_project_organization(
        project_ids,
        owner_slug="Shared",
        actor_slug="Dennis",
    )

    assert result.requested_count == 205
    assert result.affected_count == 205
    assert result.complete is True
    assert len(client.updates) == 3
    assert [len(call[1]["id"].removeprefix("in.(").removesuffix(")").split(",")) for call in client.updates] == [
        100,
        100,
        5,
    ]
    for table, _filters, payload in client.updates:
        assert table == "itineraries"
        assert payload["owner_slug"] == "shared"
        assert payload["updated_by"] == "dennis"
        assert "deleted_at" not in payload
        assert "deleted_by" not in payload


def test_bulk_organization_returns_completed_and_failed_batches_without_hiding_partial_success() -> None:
    client = ManagementClient(update_failures={1})
    repository = _repository(client)
    project_ids = [f"project-{index}" for index in range(205)]

    result = repository.bulk_update_project_organization(
        project_ids,
        folder_name="ITIN-2020",
        actor_slug="Dennis",
    )

    assert result.affected_count == 105
    assert result.complete is False
    assert len(result.failures) == 1
    assert result.failures[0].project_ids == tuple(f"project-{index}" for index in range(100, 200))
    assert result.failures[0].error == "update batch 2 failed"
    assert result.missing_ids == tuple(f"project-{index}" for index in range(100, 200))


def test_bulk_organization_does_not_mutate_legacy_lifecycle_fields() -> None:
    client = ManagementClient()
    repository = _repository(client)

    organized = repository.bulk_update_project_organization(
        ["project-1", "project-2"],
        owner_slug="Shared",
        folder_name="ITIN-2020",
        actor_slug="Christer",
    )

    assert organized.complete is True
    organization_payload = client.updates[0][2]
    assert organization_payload["owner_slug"] == "shared"
    assert organization_payload["folder_name"] == "ITIN-2020"
    assert organization_payload["updated_by"] == "christer"
    assert "deleted_at" not in organization_payload
    assert "deleted_by" not in organization_payload


def test_bulk_organization_rejects_empty_or_unsafe_project_ids_before_network_calls() -> None:
    client = ManagementClient()
    repository = _repository(client)

    with pytest.raises(ValueError, match="Select at least one"):
        repository.bulk_update_project_organization([], owner_slug="Dennis", actor_slug="Dennis")
    with pytest.raises(ValueError, match="identifiers"):
        repository.bulk_update_project_organization(
            ["project-1),deleted_at.not.is.null"],
            owner_slug="Dennis",
            actor_slug="Dennis",
        )

    assert client.updates == []

def test_permanent_delete_enumerates_more_than_200_files_and_batches_storage_cleanup() -> None:
    files = [
        {
            "id": f"file-{index}",
            "storage_path": f"itineraries/project-1/exports/file-{index}.pdf",
        }
        for index in range(205)
    ]
    client = ManagementClient(files=files)
    repository = _repository(client)

    result = repository.delete_itinerary("project-1")

    assert result.ok is True
    assert result.complete is True
    assert len(result.storage_paths) == 205
    file_gets = [params for table, params in client.gets if table == "itinerary_files"]
    assert [params["offset"] for params in file_gets] == ["0"]
    assert file_gets[0]["itinerary_id"] == "eq.project-1"
    assert client.deletes == [("itineraries", {"id": "eq.project-1"})]
    assert [len(paths) for _bucket, paths in client.storage_deletes] == [100, 100, 5]


def test_permanent_delete_reports_database_failure_after_storage_cleanup() -> None:
    calls: list[tuple[str, object]] = []

    class Client:
        def rest_get(self, table, params):
            if table == "itineraries":
                return [{"id": "project-1"}]
            return [
                {
                    "id": "file-1",
                    "itinerary_id": "project-1",
                    "storage_path": "itineraries/project-1/file.pdf",
                }
            ]

        def storage_delete(self, bucket, paths):
            calls.append(("storage", tuple(paths)))

        def rest_delete(self, table, params):
            calls.append((table, dict(params)))
            raise RuntimeError("database unavailable")

    repository = _repository(Client())

    result = repository.delete_itinerary("project-1")

    assert result.record_deleted is False
    assert result.storage_files_deleted is True
    assert result.ok is False
    assert result.complete is False
    assert result.record_error == "database unavailable"
    assert calls == [
        ("storage", ("itineraries/project-1/file.pdf",)),
        ("itineraries", {"id": "eq.project-1"}),
    ]


def test_bulk_permanent_purge_batches_projects_and_is_idempotent_for_missing_records() -> None:
    files = [
        {
            "id": f"file-{project_id}",
            "itinerary_id": project_id,
            "storage_path": f"itineraries/{project_id}/file.pdf",
        }
        for project_id in ("project-1", "project-2")
    ]
    client = ManagementClient(files=files)
    original_rest_get = client.rest_get

    def rest_get(table, params):
        rows = original_rest_get(table, params)
        if table == "itineraries":
            return [row for row in rows if row.get("id") != "project-missing"]
        return rows

    client.rest_get = rest_get

    def rest_delete(table, params):
        client.deletes.append((table, dict(params)))
        return [{"id": "project-1"}, {"id": "project-2"}]

    client.rest_delete = rest_delete
    repository = _repository(client)

    result = repository.permanently_delete_itineraries(
        ["project-1", "project-2", "project-missing"]
    )

    assert result.deleted_ids == ("project-1", "project-2", "project-missing")
    assert result.incomplete_ids == ()
    assert result.items[2].already_absent is True
    assert len([call for call in client.gets if call[0] == "itinerary_files"]) == 1
    assert client.storage_deletes == [
        (
            "itinerary-files",
            (
                "itineraries/project-1/file.pdf",
                "itineraries/project-2/file.pdf",
            ),
        )
    ]
    assert client.deletes == [
        ("itineraries", {"id": "in.(project-1,project-2,project-missing)"})
    ]


def test_bulk_permanent_purge_retains_only_projects_in_failed_storage_batch() -> None:
    class Client(ManagementClient):
        def storage_delete(self, bucket, paths):
            self.storage_deletes.append((bucket, tuple(paths)))
            if any("project-2" in path for path in paths):
                raise RuntimeError("storage unavailable")

    files = [
        {
            "id": f"file-{project_id}",
            "itinerary_id": project_id,
            "storage_path": f"itineraries/{project_id}/file.pdf",
        }
        for project_id in ("project-1", "project-2")
    ]
    client = Client(files=files)
    repository = _repository(client)

    result = repository.permanently_delete_itineraries(["project-1", "project-2"])

    assert result.deleted_ids == ()
    assert result.incomplete_ids == ("project-1", "project-2")
    assert client.deletes == []
    assert "storage unavailable" in result.items[0].result.storage_error


def test_current_explorer_list_order_has_stable_id_tie_breaker() -> None:
    client = ManagementClient()
    repository = _repository(client)

    repository.list_itineraries(sort="recent")

    params = client.gets[0][1]
    assert params["order"] == "updated_at.desc,id.asc"
