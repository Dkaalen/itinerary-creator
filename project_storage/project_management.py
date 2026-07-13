"""Rename and duplicate cloud itinerary projects without losing snapshots."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
import uuid


IdFactory = Callable[[], str]
Clock = Callable[[], datetime]


class ProjectRepository(Protocol):
    def latest_version(self, itinerary_id: str) -> dict[str, Any] | None: ...
    def upsert_itinerary(self, itinerary_id: str, *, name: str, status: str = "draft") -> dict[str, Any]: ...
    def next_version_number(self, itinerary_id: str, itinerary_type: str) -> int: ...
    def create_version(self, **kwargs: Any) -> dict[str, Any]: ...


def rename_cloud_project(project_id: str, new_name: str) -> dict[str, Any] | None:
    """Rename a cloud project and append a matching saved-project version."""

    from project_storage.runtime import get_project_storage_repository

    repository = get_project_storage_repository()
    if repository is None:
        return None
    return rename_project(repository, project_id=project_id, new_name=new_name)


def duplicate_cloud_project(project_id: str, new_name: str = "") -> dict[str, Any] | None:
    """Duplicate the latest cloud project snapshot under a new project id."""

    from project_storage.runtime import get_project_storage_repository

    repository = get_project_storage_repository()
    if repository is None:
        return None
    return duplicate_project(repository, project_id=project_id, new_name=new_name)


def rename_project(
    repository: ProjectRepository,
    *,
    project_id: str,
    new_name: str,
    clock: Clock = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    clean_id = _require_project_id(project_id)
    clean_name = _require_name(new_name)
    latest = repository.latest_version(clean_id)
    if not latest or not isinstance(latest.get("payload"), dict):
        raise ValueError("The project has no saved snapshot to rename.")
    payload = _project_payload(latest["payload"], project_id=clean_id, name=clean_name, clock=clock, duplicated=False)
    itinerary_type = _itinerary_type(latest, payload)
    repository.upsert_itinerary(clean_id, name=clean_name, status=_status(payload))
    version = repository.next_version_number(clean_id, itinerary_type)
    repository.create_version(
        itinerary_id=clean_id,
        version_number=version,
        itinerary_type=itinerary_type,
        source_type="project_rename",
        payload=payload,
    )
    return {"project_id": clean_id, "name": clean_name, "payload": payload}


def duplicate_project(
    repository: ProjectRepository,
    *,
    project_id: str,
    new_name: str = "",
    id_factory: IdFactory = lambda: str(uuid.uuid4()),
    clock: Clock = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    clean_id = _require_project_id(project_id)
    latest = repository.latest_version(clean_id)
    if not latest or not isinstance(latest.get("payload"), dict):
        raise ValueError("The project has no saved snapshot to duplicate.")
    source_metadata = latest["payload"].get("metadata")
    metadata_name = source_metadata.get("itinerary_name") if isinstance(source_metadata, dict) else ""
    original_name = str(metadata_name or "Untitled itinerary")
    clean_name = _require_name(new_name or f"{original_name} — Copy")
    duplicate_id = _require_project_id(id_factory())
    if duplicate_id == clean_id:
        raise ValueError("Duplicate project id must differ from the source project id.")
    payload = _project_payload(latest["payload"], project_id=duplicate_id, name=clean_name, clock=clock, duplicated=True)
    itinerary_type = _itinerary_type(latest, payload)
    repository.upsert_itinerary(duplicate_id, name=clean_name, status=_status(payload))
    repository.create_version(
        itinerary_id=duplicate_id,
        version_number=1,
        itinerary_type=itinerary_type,
        source_type="project_duplicate",
        payload=payload,
    )
    return {"project_id": duplicate_id, "name": clean_name, "payload": payload}


def _project_payload(
    source: dict[str, Any],
    *,
    project_id: str,
    name: str,
    clock: Clock,
    duplicated: bool,
) -> dict[str, Any]:
    payload = deepcopy(source)
    now = clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    metadata["project_id"] = project_id
    metadata["itinerary_name"] = name
    metadata["updated_at"] = now
    if duplicated:
        metadata["created_at"] = now
    payload["metadata"] = metadata
    calculator = payload.get("calculator_snapshot")
    if isinstance(calculator, dict):
        calculator["itinerary_name"] = name
    return payload


def _itinerary_type(latest: dict[str, Any], payload: dict[str, Any]) -> str:
    return str(latest.get("itinerary_type") or payload.get("output_brand") or payload.get("mode") or "agent")


def _status(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return str(metadata.get("status") or "draft")


def _require_project_id(value: object) -> str:
    clean = str(value or "").strip()
    if not clean:
        raise ValueError("Project id is required.")
    return clean


def _require_name(value: object) -> str:
    clean = " ".join(str(value or "").split())
    if not clean:
        raise ValueError("Project name cannot be blank.")
    if len(clean) > 160:
        raise ValueError("Project name must be 160 characters or fewer.")
    return clean
