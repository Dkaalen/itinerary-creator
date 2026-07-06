"""Project-browser operations for Supabase saved itineraries."""

from __future__ import annotations

from typing import Any

from project_storage.runtime import get_project_storage_repository


def list_cloud_itineraries(*, limit: int = 30) -> tuple[dict[str, Any], ...]:
    """Return saved itinerary records, newest first."""

    repository = get_project_storage_repository()
    if repository is None:
        return ()
    return tuple(repository.list_itineraries(limit=limit))


def load_latest_cloud_project_payload(itinerary_id: str) -> dict[str, Any] | None:
    """Return the latest saved-project payload for an itinerary."""

    repository = get_project_storage_repository()
    if repository is None:
        return None
    version = repository.latest_version(str(itinerary_id or "").strip())
    if not version:
        return None
    payload = version.get("payload")
    return payload if isinstance(payload, dict) else None
