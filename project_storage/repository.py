"""Repository for Supabase itinerary records and project files."""

from __future__ import annotations

from typing import Any

from project_storage.config import SupabaseStorageConfig
from project_storage.http_client import SupabaseHttpClient


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
            },
            upsert=True,
        )
        return rows[0] if rows else {}

    def list_itineraries(self, *, limit: int = 30) -> list[dict[str, Any]]:
        return self._client.rest_get(
            "itineraries",
            {
                "select": "id,name,status,created_at,updated_at",
                "order": "created_at.desc",
                "limit": str(max(1, min(int(limit), 100))),
            },
        )

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

    def upload_file(self, storage_path: str, content: bytes, *, content_type: str) -> None:
        self._client.storage_upload(self.bucket, storage_path, content, content_type=content_type)

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
