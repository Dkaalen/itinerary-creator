"""Consistency-preserving writes for canonical database project versions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import diagnostics

from project_storage.project_metadata import project_organization_from_metadata


@dataclass(frozen=True)
class ProjectVersionWriteResult:
    """Authoritative identifiers returned after one completed project save."""

    itinerary_id: str
    version_id: str
    version_number: int
    created_project: bool


def save_project_version(
    repository: Any,
    *,
    itinerary_id: str,
    name: str,
    status: str,
    itinerary_type: str,
    source_type: str,
    payload: dict[str, Any],
    project_already_persisted: bool,
) -> ProjectVersionWriteResult:
    """Write one canonical DB snapshot with compensating rollback.

    Existing projects write the immutable version first, then update list
    metadata. New projects must create their parent row first. Each branch
    compensates the remote mutation it owns if the second write fails.
    """

    version_number = repository.next_version_number(itinerary_id, itinerary_type)
    if project_already_persisted:
        return _save_existing_project(
            repository,
            itinerary_id=itinerary_id,
            name=name,
            status=status,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=payload,
            version_number=version_number,
        )
    return _save_new_project(
        repository,
        itinerary_id=itinerary_id,
        name=name,
        status=status,
        itinerary_type=itinerary_type,
        source_type=source_type,
        payload=payload,
        version_number=version_number,
    )


def _save_new_project(
    repository: Any,
    *,
    itinerary_id: str,
    name: str,
    status: str,
    itinerary_type: str,
    source_type: str,
    payload: dict[str, Any],
    version_number: int,
) -> ProjectVersionWriteResult:
    parent_created = False
    try:
        organization = project_organization_from_metadata(payload.get("metadata"))
        create_kwargs = {"organization": organization} if organization is not None else {}
        repository.create_itinerary(itinerary_id, name=name, status=status, **create_kwargs)
        parent_created = True
        version = repository.create_version(
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=payload,
        )
    except Exception:
        if parent_created:
            _best_effort_delete_new_project(repository, itinerary_id)
        raise
    return ProjectVersionWriteResult(
        itinerary_id=itinerary_id,
        version_id=str(version.get("id") or ""),
        version_number=version_number,
        created_project=True,
    )


def _save_existing_project(
    repository: Any,
    *,
    itinerary_id: str,
    name: str,
    status: str,
    itinerary_type: str,
    source_type: str,
    payload: dict[str, Any],
    version_number: int,
) -> ProjectVersionWriteResult:
    version_id = ""
    try:
        version = repository.create_version(
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=payload,
        )
        version_id = str(version.get("id") or "")
        organization = project_organization_from_metadata(payload.get("metadata"))
        update_kwargs = {"organization": organization} if organization is not None else {}
        repository.upsert_itinerary(itinerary_id, name=name, status=status, **update_kwargs)
    except Exception:
        if version_id:
            _best_effort_delete_version(repository, version_id)
        raise
    return ProjectVersionWriteResult(
        itinerary_id=itinerary_id,
        version_id=version_id,
        version_number=version_number,
        created_project=False,
    )


def _best_effort_delete_new_project(repository: Any, itinerary_id: str) -> None:
    try:
        repository.delete_itinerary(itinerary_id)
    except Exception as error:
        diagnostics.warn_exception(
            "project_storage_cleanup",
            "New project metadata could not be removed after a failed first save.",
            error,
            itinerary_id,
            source="project_storage.version_writer",
        )


def _best_effort_delete_version(repository: Any, version_id: str) -> None:
    try:
        repository.delete_version(version_id)
    except Exception as error:
        diagnostics.warn_exception(
            "project_storage_cleanup",
            "Project version could not be removed after metadata update failed.",
            error,
            version_id,
            source="project_storage.version_writer",
        )


__all__ = ["ProjectVersionWriteResult", "save_project_version"]
