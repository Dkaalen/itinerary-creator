"""Storage file write helpers with best-effort rollback."""

from __future__ import annotations

from typing import Any

import diagnostics

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PROJECT_JSON_MIME = "application/json"
PDF_MIME = "application/pdf"


def save_versioned_file(
    repository: Any,
    *,
    itinerary_id: str,
    version_number: int,
    itinerary_type: str,
    source_type: str,
    payload: dict[str, Any],
    file_type: str,
    filename: str,
    storage_path: str,
    content: bytes,
    content_type: str,
) -> None:
    """Save a versioned payload without leaving orphan files or version rows."""

    version_id = ""
    repository.upload_file(storage_path, content, content_type=content_type)
    try:
        version = repository.create_version(
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=payload,
        )
        version_id = str(version.get("id") or "")
        repository.register_file(
            itinerary_id=itinerary_id,
            version_id=version_id or None,
            file_type=file_type,
            filename=filename,
            storage_path=storage_path,
        )
    except Exception:
        best_effort_cleanup(repository, storage_path=storage_path, version_id=version_id)
        raise


def save_unversioned_file(
    repository: Any,
    *,
    itinerary_id: str,
    file_type: str,
    filename: str,
    storage_path: str,
    content: bytes,
    content_type: str,
) -> None:
    """Save a storage file and remove it if the file record cannot be registered."""

    repository.upload_file(storage_path, content, content_type=content_type)
    try:
        repository.register_file(
            itinerary_id=itinerary_id,
            file_type=file_type,
            filename=filename,
            storage_path=storage_path,
        )
    except Exception:
        best_effort_cleanup(repository, storage_path=storage_path)
        raise


def best_effort_cleanup(repository: Any, *, storage_path: str, version_id: str = "") -> None:
    """Rollback a failed file write without masking the original exception."""

    try:
        repository.delete_storage_files([storage_path])
    except Exception as error:
        diagnostics.warn_exception(
            "project_storage_cleanup",
            "Uploaded project file could not be removed after a failed save.",
            error,
            storage_path,
            source="project_storage.file_writer",
        )
    try:
        repository.delete_version(version_id)
    except Exception as error:
        diagnostics.warn_exception(
            "project_storage_cleanup",
            "Project version row could not be removed after a failed save.",
            error,
            version_id,
            source="project_storage.file_writer",
        )
