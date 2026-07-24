"""Application service boundary for cloud-project browsing and management."""

from __future__ import annotations

from typing import Any

from app_modules.project_browser_paging import PROJECT_PAGE_SIZE, ProjectPage, build_project_page
from app_modules.project_storage_runtime import get_project_storage_repository
from project_storage.delete_result import ProjectDeleteResult
from project_storage.project_browser import (
    delete_itinerary,
    delete_project_file,
    download_project_file,
    list_calculation_files,
    list_itineraries,
    load_latest_project_payload,
)
from project_storage.project_management import duplicate_project, rename_project


def list_cloud_itineraries(
    *,
    limit: int = 30,
    search: str = "",
    offset: int = 0,
    sort: str = "recent",
) -> tuple[dict[str, Any], ...]:
    repository = get_project_storage_repository()
    if repository is None:
        return ()
    return list_itineraries(repository, limit=limit, search=search, offset=offset, sort=sort)


def list_cloud_itinerary_page(
    *,
    page_index: int = 0,
    page_size: int = PROJECT_PAGE_SIZE,
    search: str = "",
    sort: str = "recent",
) -> ProjectPage:
    """Adapt repository rows into one compact UI page with lookahead."""

    clean_page = max(0, int(page_index))
    clean_size = max(1, min(int(page_size), 50))
    rows = list_cloud_itineraries(
        limit=clean_size + 1,
        offset=clean_page * clean_size,
        search=search,
        sort=sort,
    )
    return build_project_page(rows, page_index=clean_page, page_size=clean_size)


def list_cloud_calculation_files(
    itinerary_id: str,
    *,
    limit: int = 12,
) -> tuple[dict[str, Any], ...]:
    repository = get_project_storage_repository()
    if repository is None:
        return ()
    return list_calculation_files(repository, itinerary_id, limit=limit)


def download_cloud_project_file(storage_path: str) -> bytes | None:
    repository = get_project_storage_repository()
    if repository is None:
        return None
    return download_project_file(repository, storage_path)


def delete_cloud_itinerary_result(itinerary_id: str) -> ProjectDeleteResult | None:
    repository = get_project_storage_repository()
    if repository is None:
        return None
    return delete_itinerary(repository, itinerary_id)


def delete_cloud_project_file_result(
    file_id: str,
    *,
    storage_path: str = "",
) -> ProjectDeleteResult | None:
    repository = get_project_storage_repository()
    if repository is None:
        return None
    return delete_project_file(repository, file_id, storage_path=storage_path)


def delete_cloud_itinerary(itinerary_id: str) -> bool:
    """Compatibility wrapper returning whether the itinerary record was deleted."""

    result = delete_cloud_itinerary_result(itinerary_id)
    return bool(result and result.ok)


def load_latest_cloud_project_payload(itinerary_id: str) -> dict[str, Any] | None:
    repository = get_project_storage_repository()
    if repository is None:
        return None
    return load_latest_project_payload(repository, itinerary_id)


def rename_cloud_project(project_id: str, new_name: str) -> dict[str, Any] | None:
    repository = get_project_storage_repository()
    if repository is None:
        return None
    return rename_project(repository, project_id=project_id, new_name=new_name)


def duplicate_cloud_project(project_id: str, new_name: str = "") -> dict[str, Any] | None:
    repository = get_project_storage_repository()
    if repository is None:
        return None
    return duplicate_project(repository, project_id=project_id, new_name=new_name)
