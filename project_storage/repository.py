"""Repository for Supabase itinerary records and project files."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import diagnostics

from project_storage.config import SupabaseStorageConfig
from project_storage.http_client import SupabaseHttpClient
from project_storage.delete_result import ProjectDeleteResult


class ProjectStorageRepository:
    """Persist itinerary metadata, version payloads, and file references."""

    def __init__(self, config: SupabaseStorageConfig, *, client: SupabaseHttpClient | None = None) -> None:
        self._config = config
        self._client = client or SupabaseHttpClient(config)

    @property
    def bucket(self) -> str:
        return self._config.bucket

    def upsert_itinerary(self, itinerary_id: str, *, name: str, status: str = "draft") -> dict[str, Any]:
        rows = self._client.rest_insert(
            "itineraries",
            {
                "id": itinerary_id,
                "name": name or "Untitled itinerary",
                "status": status,
                "updated_at": _utc_now_iso(),
            },
            upsert=True,
        )
        return rows[0] if rows else {}

    def list_itineraries(
        self,
        *,
        limit: int = 30,
        search: str = "",
        offset: int = 0,
        sort: str = "recent",
    ) -> list[dict[str, Any]]:
        params = {
            "select": "id,name,status,created_at,updated_at",
            "order": _project_order(sort),
            "limit": str(max(1, min(int(limit), 100))),
            "offset": str(max(0, int(offset))),
        }
        query = " ".join(str(search or "").split())
        if query:
            params["name"] = f"ilike.*{_escape_like(query)}*"
        return self._client.rest_get("itineraries", params)

    def latest_version(self, itinerary_id: str) -> dict[str, Any] | None:
        rows = self._client.rest_get(
            "itinerary_versions",
            {
                "select": "id,itinerary_id,version_number,itinerary_type,source_type,payload,created_at",
                "itinerary_id": f"eq.{itinerary_id}",
                "order": "created_at.desc",
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
                "order": "version_number.desc",
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

    def list_files(self, itinerary_id: str, *, file_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        params = {
            "select": "id,itinerary_id,version_id,file_type,filename,storage_path,created_at",
            "itinerary_id": f"eq.{itinerary_id}",
            "order": "created_at.desc",
            "limit": str(max(1, min(int(limit), 200))),
        }
        if file_type:
            params["file_type"] = f"eq.{file_type}"
        return self._client.rest_get("itinerary_files", params)

    def upload_file(self, storage_path: str, content: bytes, *, content_type: str) -> None:
        self._client.storage_upload(self.bucket, storage_path, content, content_type=content_type)

    def download_file(self, storage_path: str) -> bytes:
        return self._client.storage_download(self.bucket, storage_path)

    def delete_storage_files(self, storage_paths: list[str]) -> None:
        paths = [path for path in (str(item or "").strip() for item in storage_paths) if path]
        if paths:
            self._client.storage_delete(self.bucket, paths)

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

    def delete_file(self, file_id: str, *, storage_path: str = "") -> ProjectDeleteResult:
        """Delete one registered file and best-effort remove its storage object."""

        clean_file_id = str(file_id or "").strip()
        clean_storage_path = str(storage_path or "").strip()
        if not clean_file_id and not clean_storage_path:
            return ProjectDeleteResult(itinerary_id="", record_deleted=False, storage_files_deleted=False)

        if clean_file_id:
            self._client.rest_delete("itinerary_files", {"id": f"eq.{clean_file_id}"})

        if not clean_storage_path:
            return ProjectDeleteResult(itinerary_id="", record_deleted=True, storage_files_deleted=True)

        try:
            self.delete_storage_files([clean_storage_path])
        except Exception as exc:
            diagnostics.warn_exception(
                "project_storage_delete",
                "Storage object could not be removed after deleting its file record.",
                exc,
                clean_storage_path,
                source="project_storage.repository",
            )
            return ProjectDeleteResult(
                itinerary_id="",
                storage_paths=(clean_storage_path,),
                record_deleted=True,
                storage_files_deleted=False,
                storage_error=str(exc),
            )
        return ProjectDeleteResult(
            itinerary_id="",
            storage_paths=(clean_storage_path,),
            record_deleted=True,
            storage_files_deleted=True,
        )

    def delete_itinerary(self, itinerary_id: str) -> ProjectDeleteResult:
        clean_id = str(itinerary_id or "").strip()
        if not clean_id:
            return ProjectDeleteResult(itinerary_id="", record_deleted=False, storage_files_deleted=False)

        files = self.list_files(clean_id, limit=200)
        storage_paths = tuple(str(item.get("storage_path") or "").strip() for item in files)
        storage_paths = tuple(path for path in storage_paths if path)
        self._client.rest_delete("itineraries", {"id": f"eq.{clean_id}"})

        if not storage_paths:
            return ProjectDeleteResult(itinerary_id=clean_id, record_deleted=True, storage_files_deleted=True)

        try:
            self.delete_storage_files(list(storage_paths))
        except Exception as exc:
            diagnostics.warn_exception(
                "project_storage_delete",
                "One or more itinerary storage objects could not be removed after deleting the itinerary record.",
                exc,
                ", ".join(storage_paths),
                source="project_storage.repository",
            )
            return ProjectDeleteResult(
                itinerary_id=clean_id,
                storage_paths=storage_paths,
                record_deleted=True,
                storage_files_deleted=False,
                storage_error=str(exc),
            )
        return ProjectDeleteResult(
            itinerary_id=clean_id,
            storage_paths=storage_paths,
            record_deleted=True,
            storage_files_deleted=True,
        )


def _project_order(value: object) -> str:
    return {
        "oldest": "updated_at.asc",
        "name": "name.asc",
        "created_recent": "created_at.desc",
        "created_oldest": "created_at.asc",
    }.get(str(value or "").strip().casefold(), "updated_at.desc")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _escape_like(value: str) -> str:
    return value.replace("*", "").replace("%", "").replace("_", "").replace(",", " ")[:80]
