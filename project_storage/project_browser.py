"""Repository-facing operations for saved itinerary records and files."""

from __future__ import annotations

from typing import Any, Protocol

from project_storage.delete_result import ProjectDeleteResult

CALCULATOR_FILE_TYPE = "calculator_xlsx"


class ProjectBrowserRepository(Protocol):
    """Minimal repository contract needed by project-browser operations."""

    def list_itineraries(
        self,
        *,
        limit: int,
        search: str,
        offset: int,
        sort: str,
    ) -> list[dict[str, Any]]: ...

    def list_files(
        self,
        itinerary_id: str,
        *,
        file_type: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def download_file(self, storage_path: str) -> bytes: ...

    def delete_itinerary(self, itinerary_id: str) -> ProjectDeleteResult: ...

    def delete_file(self, file_id: str, *, storage_path: str = "") -> ProjectDeleteResult: ...

    def latest_version(self, itinerary_id: str) -> dict[str, Any] | None: ...


def list_itineraries(
    repository: ProjectBrowserRepository,
    *,
    limit: int = 30,
    search: str = "",
    offset: int = 0,
    sort: str = "recent",
) -> tuple[dict[str, Any], ...]:
    """Return a bounded set of saved itinerary records."""

    return tuple(repository.list_itineraries(limit=limit, search=search, offset=offset, sort=sort))


def list_calculation_files(
    repository: ProjectBrowserRepository,
    itinerary_id: str,
    *,
    limit: int = 12,
) -> tuple[dict[str, Any], ...]:
    """Return saved calculator workbook records for an itinerary."""

    return tuple(
        repository.list_files(
            str(itinerary_id or "").strip(),
            file_type=CALCULATOR_FILE_TYPE,
            limit=limit,
        )
    )


def download_project_file(repository: ProjectBrowserRepository, storage_path: str) -> bytes:
    """Return file bytes from private project storage."""

    return repository.download_file(str(storage_path or "").strip())


def delete_itinerary(repository: ProjectBrowserRepository, itinerary_id: str) -> ProjectDeleteResult:
    """Delete one itinerary record and best-effort cleanup its registered files."""

    return repository.delete_itinerary(str(itinerary_id or "").strip())


def delete_project_file(
    repository: ProjectBrowserRepository,
    file_id: str,
    *,
    storage_path: str = "",
) -> ProjectDeleteResult:
    """Delete one registered project file and best-effort cleanup its storage object."""

    return repository.delete_file(
        str(file_id or "").strip(),
        storage_path=str(storage_path or "").strip(),
    )


def load_latest_project_payload(
    repository: ProjectBrowserRepository,
    itinerary_id: str,
) -> dict[str, Any] | None:
    """Return the latest saved-project payload for an itinerary."""

    version = repository.latest_version(str(itinerary_id or "").strip())
    if not version:
        return None
    payload = version.get("payload")
    return payload if isinstance(payload, dict) else None
