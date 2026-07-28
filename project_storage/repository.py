"""Repository for Supabase itinerary records and project files."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Iterable

import diagnostics

from project_storage.config import SupabaseStorageConfig
from project_storage.delete_result import ProjectDeleteResult
from project_storage.http_client import SupabaseHttpClient
from project_storage.project_metadata import (
    ProjectOrganization,
    normalize_project_actor,
    normalize_project_folder,
    normalize_project_owner,
)
from project_storage.project_results import (
    ProjectBulkMutationFailure,
    ProjectBulkMutationResult,
    ProjectBulkPurgeResult,
    ProjectFolderOption,
    ProjectListResult,
    ProjectPurgeItemResult,
)

_MANAGEMENT_SELECT = (
    "id,name,status,created_at,updated_at,owner_slug,folder_name,created_by,"
    "updated_by,revision,last_saved_at,deleted_at,deleted_by"
)
_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_BULK_PATCH_SIZE = 100
_FILE_PAGE_SIZE = 200


class ProjectStorageRepository:
    """Persist itinerary metadata, version payloads, and file references."""

    def __init__(self, config: SupabaseStorageConfig, *, client: SupabaseHttpClient | None = None) -> None:
        self._config = config
        self._client = client or SupabaseHttpClient(config)

    @property
    def bucket(self) -> str:
        return self._config.bucket

    def create_itinerary(
        self,
        itinerary_id: str,
        *,
        name: str,
        status: str = "draft",
        organization: ProjectOrganization | None = None,
    ) -> dict[str, Any]:
        """Insert one new itinerary and fail if that stable id already exists."""

        payload: dict[str, Any] = {
            "id": itinerary_id,
            "name": name or "Untitled itinerary",
            "status": status,
            "updated_at": _utc_now_iso(),
        }
        if organization is not None:
            payload.update(_organization_insert_fields(organization))
        rows = self._client.rest_insert("itineraries", payload)
        return rows[0] if rows else {}

    def upsert_itinerary(
        self,
        itinerary_id: str,
        *,
        name: str,
        status: str = "draft",
        organization: ProjectOrganization | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": itinerary_id,
            "name": name or "Untitled itinerary",
            "status": status,
            "updated_at": _utc_now_iso(),
        }
        if organization is not None:
            payload.update(_organization_update_fields(organization))
        rows = self._client.rest_insert("itineraries", payload, upsert=True)
        return rows[0] if rows else {}

    def list_itineraries(
        self,
        *,
        limit: int = 30,
        search: str = "",
        offset: int = 0,
        sort: str = "recent",
    ) -> list[dict[str, Any]]:
        """Return the legacy active-project list used by the current Explorer UI."""

        params = {
            "select": "id,name,status,created_at,updated_at",
            "order": _project_order(sort),
            "limit": str(max(1, min(int(limit), 100))),
            "offset": str(max(0, int(offset))),
        }
        query = " ".join(str(search or "").split())
        if query:
            escaped = _escape_like(query)
            if escaped:
                params["name"] = f"ilike.*{escaped}*"
        return self._client.rest_get("itineraries", params)

    def list_project_page(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        search: str = "",
        sort: str = "recent",
        owner_slug: str = "",
        folder_name: str = "",
        include_trashed: bool = False,
        trash_only: bool = False,
    ) -> ProjectListResult:
        """Return an exact-count management page using the additive schema."""

        params = {
            "select": _MANAGEMENT_SELECT,
            "order": _management_project_order(sort),
            "limit": str(max(1, min(int(limit), 100))),
            "offset": str(max(0, int(offset))),
        }
        query = " ".join(str(search or "").split())
        if query:
            escaped = _escape_like(query)
            if escaped:
                params["or"] = f"(name.ilike.*{escaped}*,folder_name.ilike.*{escaped}*)"
        if owner_slug:
            params["owner_slug"] = f"eq.{normalize_project_owner(owner_slug)}"
        if folder_name:
            params["folder_name"] = f"eq.{normalize_project_folder(folder_name)}"
        if trash_only:
            params["deleted_at"] = "not.is.null"
        elif not include_trashed:
            params["deleted_at"] = "is.null"
        rows, total = self._client.rest_get_with_count("itineraries", params)
        return ProjectListResult(projects=tuple(rows), total_count=total)

    def list_project_folders(
        self,
        *,
        owner_slug: str = "",
        include_trashed: bool = False,
    ) -> tuple[ProjectFolderOption, ...]:
        """Return server-owned logical folder options for Explorer filters."""

        clean_owner = normalize_project_owner(owner_slug) if owner_slug else None
        rows = self._client.rest_rpc(
            "list_project_folders",
            {
                "p_owner_slug": clean_owner,
                "p_include_trashed": bool(include_trashed),
            },
        )
        options: list[ProjectFolderOption] = []
        for row in rows:
            folder = normalize_project_folder(row.get("folder_name"))
            if not folder:
                continue
            try:
                count = max(0, int(row.get("project_count") or 0))
            except (TypeError, ValueError):
                count = 0
            options.append(ProjectFolderOption(folder_name=folder, project_count=count))
        return tuple(options)

    def latest_version(self, itinerary_id: str) -> dict[str, Any] | None:
        rows = self._client.rest_get(
            "itinerary_versions",
            {
                "select": "id,itinerary_id,version_number,itinerary_type,source_type,payload,created_at",
                "itinerary_id": f"eq.{itinerary_id}",
                "order": "created_at.desc,id.asc",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def next_version_number(self, itinerary_id: str, itinerary_type: str) -> int:
        rows = self._client.rest_get(
            "itinerary_versions",
            {
                "select": "version_number",
                "itinerary_id": f"eq.{itinerary_id}",
                "itinerary_type": f"eq.{itinerary_type}",
                "order": "version_number.desc,id.asc",
                "limit": "1",
            },
        )
        if not rows:
            return 1
        return int(rows[0].get("version_number") or 0) + 1

    def create_version(
        self,
        *,
        itinerary_id: str,
        version_number: int,
        itinerary_type: str,
        source_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        rows = self._client.rest_insert(
            "itinerary_versions",
            {
                "itinerary_id": itinerary_id,
                "version_number": version_number,
                "itinerary_type": itinerary_type,
                "source_type": source_type,
                "payload": payload,
            },
        )
        return rows[0] if rows else {}

    def list_files(
        self,
        itinerary_id: str,
        *,
        file_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params = {
            "select": "id,itinerary_id,version_id,file_type,filename,storage_path,created_at",
            "itinerary_id": f"eq.{itinerary_id}",
            "order": "created_at.desc,id.asc",
            "limit": str(max(1, min(int(limit), _FILE_PAGE_SIZE))),
            "offset": str(max(0, int(offset))),
        }
        if file_type:
            params["file_type"] = f"eq.{file_type}"
        return self._client.rest_get("itinerary_files", params)

    def list_all_files(self, itinerary_id: str, *, file_type: str | None = None) -> list[dict[str, Any]]:
        """Read every registered file without the former 200-record cleanup cap."""

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        offset = 0
        while True:
            page = self.list_files(
                itinerary_id,
                file_type=file_type,
                limit=_FILE_PAGE_SIZE,
                offset=offset,
            )
            if not page:
                break
            added = 0
            for item in page:
                identity = str(item.get("id") or item.get("storage_path") or "").strip()
                if identity and identity in seen:
                    continue
                if identity:
                    seen.add(identity)
                rows.append(item)
                added += 1
            if len(page) < _FILE_PAGE_SIZE or added == 0:
                break
            offset += len(page)
        return rows

    def upload_file(self, storage_path: str, content: bytes, *, content_type: str) -> None:
        self._client.storage_upload(self.bucket, storage_path, content, content_type=content_type)

    def download_file(self, storage_path: str) -> bytes:
        return self._client.storage_download(self.bucket, storage_path)

    def delete_storage_files(self, storage_paths: list[str]) -> None:
        paths = [path for path in (str(item or "").strip() for item in storage_paths) if path]
        for batch in _chunks(paths, _BULK_PATCH_SIZE):
            self._client.storage_delete(self.bucket, list(batch))

    def register_file(
        self,
        *,
        itinerary_id: str,
        file_type: str,
        filename: str,
        storage_path: str,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "itinerary_id": itinerary_id,
            "file_type": file_type,
            "filename": filename,
            "storage_path": storage_path,
        }
        if version_id:
            payload["version_id"] = version_id
        rows = self._client.rest_insert("itinerary_files", payload)
        return rows[0] if rows else {}

    def delete_version(self, version_id: str) -> None:
        clean_id = str(version_id or "").strip()
        if clean_id:
            self._client.rest_delete("itinerary_versions", {"id": f"eq.{clean_id}"})

    def update_project_organization(
        self,
        itinerary_id: str,
        *,
        owner_slug: object,
        folder_name: object,
        actor_slug: object,
    ) -> dict[str, Any]:
        """Update owner/folder metadata for one active or trashed project."""

        result = self.bulk_update_project_organization(
            [itinerary_id],
            owner_slug=owner_slug,
            folder_name=folder_name,
            actor_slug=actor_slug,
        )
        if not result.affected_ids:
            return {}
        rows = self._client.rest_get(
            "itineraries",
            {"select": _MANAGEMENT_SELECT, "id": f"eq.{result.affected_ids[0]}", "limit": "1"},
        )
        return rows[0] if rows else {}

    def bulk_update_project_organization(
        self,
        itinerary_ids: Iterable[object],
        *,
        owner_slug: object | None = None,
        folder_name: object | None = None,
        actor_slug: object = "unassigned",
    ) -> ProjectBulkMutationResult:
        """Apply owner and/or folder metadata to a bounded set of projects."""

        requested_ids = _normalize_project_ids(itinerary_ids)
        payload: dict[str, Any] = {
            "updated_by": normalize_project_actor(actor_slug),
            "updated_at": _utc_now_iso(),
        }
        if owner_slug is not None:
            payload["owner_slug"] = normalize_project_owner(owner_slug)
        if folder_name is not None:
            payload["folder_name"] = normalize_project_folder(folder_name)
        if len(payload) == 2:
            raise ValueError("Choose an owner or folder to update.")
        return self._bulk_patch_itineraries(requested_ids, payload)

    def move_itineraries_to_trash(
        self,
        itinerary_ids: Iterable[object],
        *,
        actor_slug: object,
    ) -> ProjectBulkMutationResult:
        """Soft-delete projects without removing versions or files."""

        requested_ids = _normalize_project_ids(itinerary_ids)
        actor = normalize_project_actor(actor_slug)
        timestamp = _utc_now_iso()
        return self._bulk_patch_itineraries(
            requested_ids,
            {
                "deleted_at": timestamp,
                "deleted_by": actor,
                "updated_by": actor,
                "updated_at": timestamp,
            },
        )

    def restore_itineraries_from_trash(
        self,
        itinerary_ids: Iterable[object],
        *,
        actor_slug: object,
    ) -> ProjectBulkMutationResult:
        """Restore soft-deleted projects without altering their saved content."""

        requested_ids = _normalize_project_ids(itinerary_ids)
        actor = normalize_project_actor(actor_slug)
        return self._bulk_patch_itineraries(
            requested_ids,
            {
                "deleted_at": None,
                "deleted_by": None,
                "updated_by": actor,
                "updated_at": _utc_now_iso(),
            },
        )

    def _bulk_patch_itineraries(
        self,
        requested_ids: tuple[str, ...],
        payload: dict[str, Any],
    ) -> ProjectBulkMutationResult:
        affected_ids: list[str] = []
        failures: list[ProjectBulkMutationFailure] = []
        for batch in _chunks(requested_ids, _BULK_PATCH_SIZE):
            try:
                rows = self._client.rest_update(
                    "itineraries",
                    {"id": _in_filter(batch)},
                    payload,
                )
            except Exception as exc:
                diagnostics.warn_exception(
                    "project_storage_bulk_update",
                    "One project-management batch could not be updated.",
                    exc,
                    ", ".join(batch),
                    source="project_storage.repository",
                )
                failures.append(ProjectBulkMutationFailure(project_ids=batch, error=str(exc)))
                continue
            affected_ids.extend(str(row.get("id") or "").strip() for row in rows if row.get("id"))
        affected_set = set(affected_ids)
        ordered_affected = tuple(project_id for project_id in requested_ids if project_id in affected_set)
        return ProjectBulkMutationResult(
            requested_ids=requested_ids,
            affected_ids=ordered_affected,
            failures=tuple(failures),
        )

    def delete_file(self, file_id: str, *, storage_path: str = "") -> ProjectDeleteResult:
        """Delete one registered file without orphaning an unrecoverable object."""

        clean_file_id = str(file_id or "").strip()
        clean_storage_path = str(storage_path or "").strip()
        if not clean_file_id and not clean_storage_path:
            return ProjectDeleteResult(itinerary_id="", record_deleted=False, storage_files_deleted=False)

        storage_paths = (clean_storage_path,) if clean_storage_path else ()
        if clean_storage_path:
            try:
                self.delete_storage_files([clean_storage_path])
            except Exception as exc:
                diagnostics.warn_exception(
                    "project_storage_delete",
                    "Project file storage cleanup failed; its database record was retained for retry.",
                    exc,
                    clean_storage_path,
                    source="project_storage.repository",
                )
                return ProjectDeleteResult(
                    itinerary_id="",
                    storage_paths=storage_paths,
                    record_deleted=False,
                    storage_files_deleted=False,
                    storage_error=str(exc),
                )

        if clean_file_id:
            try:
                self._client.rest_delete("itinerary_files", {"id": f"eq.{clean_file_id}"})
            except Exception as exc:
                diagnostics.warn_exception(
                    "project_storage_delete",
                    "Project file record could not be removed after storage cleanup.",
                    exc,
                    clean_file_id,
                    source="project_storage.repository",
                )
                return ProjectDeleteResult(
                    itinerary_id="",
                    storage_paths=storage_paths,
                    record_deleted=False,
                    storage_files_deleted=True,
                    record_error=str(exc),
                )

        return ProjectDeleteResult(
            itinerary_id="",
            storage_paths=storage_paths,
            record_deleted=True,
            storage_files_deleted=True,
        )

    def permanently_delete_itineraries(
        self,
        itinerary_ids: Iterable[object],
    ) -> ProjectBulkPurgeResult:
        """Permanently purge active or legacy-soft-deleted projects.

        The application no longer exposes a Trash lifecycle. Database records
        are retained whenever Storage cleanup fails so the user can retry.
        """

        requested_ids = _normalize_project_ids(itinerary_ids)
        existing_ids = self._existing_project_ids(requested_ids)
        items: list[ProjectPurgeItemResult] = []
        for project_id in requested_ids:
            if project_id not in existing_ids:
                items.append(ProjectPurgeItemResult(project_id=project_id, error="Project was not found."))
                continue
            try:
                result = self.delete_itinerary(project_id)
            except Exception as exc:
                diagnostics.warn_exception(
                    "project_storage_delete",
                    "A selected itinerary could not be permanently deleted.",
                    exc,
                    project_id,
                    source="project_storage.repository",
                )
                items.append(ProjectPurgeItemResult(project_id=project_id, error=str(exc)))
                continue
            items.append(ProjectPurgeItemResult(project_id=project_id, result=result))
        return ProjectBulkPurgeResult(items=tuple(items))

    def _existing_project_ids(self, requested_ids: tuple[str, ...]) -> set[str]:
        existing: set[str] = set()
        for batch in _chunks(requested_ids, _BULK_PATCH_SIZE):
            rows = self._client.rest_get(
                "itineraries",
                {
                    "select": "id",
                    "id": _in_filter(batch),
                    "limit": str(len(batch)),
                },
            )
            existing.update(
                str(row.get("id") or "").strip()
                for row in rows
                if str(row.get("id") or "").strip()
            )
        return existing

    def delete_itinerary(self, itinerary_id: str) -> ProjectDeleteResult:
        """Permanently delete one project without losing failed-cleanup retry state."""

        clean_id = str(itinerary_id or "").strip()
        if not clean_id:
            return ProjectDeleteResult(itinerary_id="", record_deleted=False, storage_files_deleted=False)

        files = self.list_all_files(clean_id)
        storage_paths = tuple(str(item.get("storage_path") or "").strip() for item in files)
        storage_paths = tuple(dict.fromkeys(path for path in storage_paths if path))

        if storage_paths:
            try:
                self.delete_storage_files(list(storage_paths))
            except Exception as exc:
                diagnostics.warn_exception(
                    "project_storage_delete",
                    "Itinerary storage cleanup failed; the project record was retained for retry.",
                    exc,
                    ", ".join(storage_paths),
                    source="project_storage.repository",
                )
                return ProjectDeleteResult(
                    itinerary_id=clean_id,
                    storage_paths=storage_paths,
                    record_deleted=False,
                    storage_files_deleted=False,
                    storage_error=str(exc),
                )

        try:
            self._client.rest_delete("itineraries", {"id": f"eq.{clean_id}"})
        except Exception as exc:
            diagnostics.warn_exception(
                "project_storage_delete",
                "Itinerary record could not be removed after storage cleanup.",
                exc,
                clean_id,
                source="project_storage.repository",
            )
            return ProjectDeleteResult(
                itinerary_id=clean_id,
                storage_paths=storage_paths,
                record_deleted=False,
                storage_files_deleted=True,
                record_error=str(exc),
            )

        return ProjectDeleteResult(
            itinerary_id=clean_id,
            storage_paths=storage_paths,
            record_deleted=True,
            storage_files_deleted=True,
        )


def _organization_insert_fields(organization: ProjectOrganization) -> dict[str, Any]:
    return {
        "owner_slug": organization.owner_slug,
        "folder_name": organization.folder_name,
        "created_by": organization.actor_slug,
        "updated_by": organization.actor_slug,
    }


def _organization_update_fields(organization: ProjectOrganization) -> dict[str, Any]:
    return {
        "owner_slug": organization.owner_slug,
        "folder_name": organization.folder_name,
        "updated_by": organization.actor_slug,
    }


def _project_order(value: object) -> str:
    return {
        "oldest": "updated_at.asc,id.asc",
        "name": "name.asc,id.asc",
        "created_recent": "created_at.desc,id.asc",
        "created_oldest": "created_at.asc,id.asc",
    }.get(str(value or "").strip().casefold(), "updated_at.desc,id.asc")


def _management_project_order(value: object) -> str:
    return {
        "oldest": "last_saved_at.asc,id.asc",
        "name": "name.asc,id.asc",
        "created_recent": "created_at.desc,id.asc",
        "created_oldest": "created_at.asc,id.asc",
        "owner": "owner_slug.asc,last_saved_at.desc,id.asc",
        "folder": "folder_name.asc,last_saved_at.desc,id.asc",
        "trash_recent": "deleted_at.desc,id.asc",
    }.get(str(value or "").strip().casefold(), "last_saved_at.desc,id.asc")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _escape_like(value: str) -> str:
    safe = "".join(
        character
        for character in str(value or "")
        if character.isalnum() or character in " -'&"
    )
    return " ".join(safe.split())[:80]


def _normalize_project_ids(values: Iterable[object]) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value or "").strip()
        if not clean or clean in seen:
            continue
        if not _PROJECT_ID_PATTERN.fullmatch(clean):
            raise ValueError("One or more project identifiers are invalid.")
        seen.add(clean)
        ids.append(clean)
    if not ids:
        raise ValueError("Select at least one project.")
    return tuple(ids)


def _in_filter(values: Iterable[str]) -> str:
    return f"in.({','.join(values)})"


def _chunks(values: Iterable[Any], size: int) -> Iterable[tuple[Any, ...]]:
    batch: list[Any] = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield tuple(batch)
            batch = []
    if batch:
        yield tuple(batch)
