"""Project-browser operations for Supabase saved itineraries."""

from __future__ import annotations

from typing import Any

from app_modules.project_browser_paging import PROJECT_PAGE_SIZE, ProjectPage, build_project_page
from project_storage.delete_result import ProjectDeleteResult
from project_storage.runtime import get_project_storage_repository

CALCULATOR_FILE_TYPE = "calculator_xlsx"


def list_cloud_itineraries(
    *,
    limit: int = 30,
    search: str = "",
    offset: int = 0,
    sort: str = "recent",
) -> tuple[dict[str, Any], ...]:
    """Return a bounded set of saved itinerary records."""

    repository = get_project_storage_repository()
    if repository is None:
        return ()
    return tuple(repository.list_itineraries(limit=limit, search=search, offset=offset, sort=sort))


def list_cloud_itinerary_page(
    *,
    page_index: int = 0,
    page_size: int = PROJECT_PAGE_SIZE,
    search: str = "",
    sort: str = "recent",
) -> ProjectPage:
    """Return one page plus a one-row lookahead for Next navigation."""

    clean_page = max(0, int(page_index))
    clean_size = max(1, min(int(page_size), 50))
    rows = list_cloud_itineraries(
        limit=clean_size + 1,
        offset=clean_page * clean_size,
        search=search,
        sort=sort,
    )
    return build_project_page(rows, page_index=clean_page, page_size=clean_size)


def list_cloud_calculation_files(itinerary_id: str, *, limit: int = 12) -> tuple[dict[str, Any], ...]:
    """Return saved calculator workbook records for an itinerary."""

    repository = get_project_storage_repository()
    if repository is None:
        return ()
    return tuple(repository.list_files(str(itinerary_id or "").strip(), file_type=CALCULATOR_FILE_TYPE, limit=limit))


def download_cloud_project_file(storage_path: str) -> bytes | None:
    """Return file bytes from private Supabase storage."""

    repository = get_project_storage_repository()
    if repository is None:
        return None
    return repository.download_file(str(storage_path or "").strip())


def delete_cloud_itinerary_result(itinerary_id: str) -> ProjectDeleteResult | None:
    """Delete an itinerary record and best-effort cleanup its registered files."""

    repository = get_project_storage_repository()
    if repository is None:
        return None
    return repository.delete_itinerary(str(itinerary_id or "").strip())


def delete_cloud_project_file_result(file_id: str, *, storage_path: str = "") -> ProjectDeleteResult | None:
    """Delete one registered project file and best-effort cleanup its storage object."""

    repository = get_project_storage_repository()
    if repository is None:
        return None
    return repository.delete_file(str(file_id or "").strip(), storage_path=str(storage_path or "").strip())


def delete_cloud_itinerary(itinerary_id: str) -> bool:
    """Compatibility wrapper returning whether the itinerary record was deleted."""

    result = delete_cloud_itinerary_result(itinerary_id)
    return bool(result and result.ok)


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
