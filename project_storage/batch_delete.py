"""Batched permanent deletion for saved projects and registered files."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import diagnostics

from project_storage.delete_result import ProjectDeleteResult
from project_storage.project_results import ProjectBulkPurgeResult, ProjectPurgeItemResult

_FILE_PAGE_SIZE = 500
_STORAGE_BATCH_SIZE = 100
_DATABASE_BATCH_SIZE = 100


def permanently_delete_project_batch(
    *,
    client: Any,
    bucket: str,
    requested_ids: tuple[str, ...],
) -> ProjectBulkPurgeResult:
    """Delete many projects with bounded network batches and retry-safe outcomes."""

    files_by_project = _files_by_project(client, requested_ids)

    storage_failures: dict[str, str] = {}
    storage_paths_by_project = {
        project_id: tuple(
            dict.fromkeys(
                str(item.get("storage_path") or "").strip()
                for item in files_by_project.get(project_id, ())
                if str(item.get("storage_path") or "").strip()
            )
        )
        for project_id in requested_ids
    }
    path_owners: dict[str, set[str]] = defaultdict(set)
    for project_id, paths in storage_paths_by_project.items():
        for path in paths:
            path_owners[path].add(project_id)
    for batch in _chunks(tuple(path_owners), _STORAGE_BATCH_SIZE):
        try:
            client.storage_delete(bucket, list(batch))
        except Exception as exc:
            affected = tuple(
                dict.fromkeys(
                    project_id
                    for path in batch
                    for project_id in sorted(path_owners[path])
                )
            )
            diagnostics.warn_exception(
                "project_storage_delete",
                "One project-file storage batch could not be deleted; affected project records were retained.",
                exc,
                ", ".join(affected),
                source="project_storage.batch_delete",
            )
            for project_id in affected:
                storage_failures.setdefault(project_id, str(exc))

    clean_project_ids = tuple(
        project_id for project_id in requested_ids if project_id not in storage_failures
    )
    record_deleted: set[str] = set()
    already_absent: set[str] = set()
    record_failures: dict[str, str] = {}
    for batch in _chunks(clean_project_ids, _DATABASE_BATCH_SIZE):
        try:
            rows = client.rest_delete("itineraries", {"id": _id_filter(batch)})
        except Exception as exc:
            diagnostics.warn_exception(
                "project_storage_delete",
                "One project-record deletion batch failed after Storage cleanup.",
                exc,
                ", ".join(batch),
                source="project_storage.batch_delete",
            )
            for project_id in batch:
                record_failures[project_id] = str(exc)
            continue
        returned = {
            str(row.get("id") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        # PostgREST may be configured not to return deleted representations.
        if returned:
            record_deleted.update(returned)
            already_absent.update(project_id for project_id in batch if project_id not in returned)
        else:
            record_deleted.update(batch)

    items: list[ProjectPurgeItemResult] = []
    for project_id in requested_ids:
        paths = storage_paths_by_project.get(project_id, ())
        if project_id in storage_failures:
            items.append(
                ProjectPurgeItemResult(
                    project_id=project_id,
                    result=ProjectDeleteResult(
                        itinerary_id=project_id,
                        storage_paths=paths,
                        record_deleted=False,
                        storage_files_deleted=False,
                        storage_error=storage_failures[project_id],
                    ),
                )
            )
            continue
        if project_id in record_failures or (project_id not in record_deleted and project_id not in already_absent):
            error = record_failures.get(project_id, "Project record was not deleted.")
            items.append(
                ProjectPurgeItemResult(
                    project_id=project_id,
                    result=ProjectDeleteResult(
                        itinerary_id=project_id,
                        storage_paths=paths,
                        record_deleted=False,
                        storage_files_deleted=True,
                        record_error=error,
                    ),
                )
            )
            continue
        items.append(
            ProjectPurgeItemResult(
                project_id=project_id,
                result=ProjectDeleteResult(
                    itinerary_id=project_id,
                    storage_paths=paths,
                    record_deleted=project_id not in already_absent,
                    storage_files_deleted=True,
                ),
                already_absent=project_id in already_absent,
            )
        )
    return ProjectBulkPurgeResult(items=tuple(items))


def _files_by_project(client: Any, project_ids: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for batch in _chunks(project_ids, _DATABASE_BATCH_SIZE):
        offset = 0
        while batch:
            rows = client.rest_get(
                "itinerary_files",
                {
                    "select": "id,itinerary_id,storage_path",
                    "itinerary_id": _id_filter(batch),
                    "order": "itinerary_id.asc,created_at.asc,id.asc",
                    "limit": str(_FILE_PAGE_SIZE),
                    "offset": str(offset),
                },
            )
            for row in rows:
                project_id = str(row.get("itinerary_id") or "").strip()
                if not project_id and len(batch) == 1:
                    project_id = batch[0]
                if project_id in batch:
                    grouped[project_id].append(row)
            if len(rows) < _FILE_PAGE_SIZE:
                break
            offset += len(rows)
    return grouped


def _id_filter(values: tuple[str, ...]) -> str:
    if len(values) == 1:
        return f"eq.{values[0]}"
    return f"in.({','.join(values)})"


def _chunks(values: Iterable[str], size: int) -> Iterable[tuple[str, ...]]:
    batch: list[str] = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield tuple(batch)
            batch = []
    if batch:
        yield tuple(batch)


__all__ = ["permanently_delete_project_batch"]
