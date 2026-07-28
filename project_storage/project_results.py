"""Immutable result models for project listing and bulk mutations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from project_storage.delete_result import ProjectDeleteResult


@dataclass(frozen=True)
class ProjectListResult:
    """One exact-count project query result."""

    projects: tuple[dict[str, Any], ...]
    total_count: int


@dataclass(frozen=True)
class ProjectFolderOption:
    """One logical folder/reference with its active project count."""

    folder_name: str
    project_count: int


@dataclass(frozen=True)
class ProjectBulkMutationFailure:
    """One failed network batch from a bulk project mutation."""

    project_ids: tuple[str, ...]
    error: str


@dataclass(frozen=True)
class ProjectBulkMutationResult:
    """Result of one repository-owned bulk project mutation."""

    requested_ids: tuple[str, ...]
    affected_ids: tuple[str, ...]
    failures: tuple[ProjectBulkMutationFailure, ...] = ()

    @property
    def requested_count(self) -> int:
        return len(self.requested_ids)

    @property
    def affected_count(self) -> int:
        return len(self.affected_ids)

    @property
    def missing_ids(self) -> tuple[str, ...]:
        affected = set(self.affected_ids)
        return tuple(project_id for project_id in self.requested_ids if project_id not in affected)

    @property
    def complete(self) -> bool:
        return not self.missing_ids and not self.failures


@dataclass(frozen=True)
class ProjectPurgeItemResult:
    """Permanent-purge outcome for one selected project."""

    project_id: str
    result: ProjectDeleteResult | None = None
    error: str = ""
    already_absent: bool = False

    @property
    def record_deleted(self) -> bool:
        return bool(self.result and self.result.record_deleted)

    @property
    def complete(self) -> bool:
        return bool(self.already_absent or (self.result and self.result.complete and not self.error))

    @property
    def deleted_or_absent(self) -> bool:
        return self.record_deleted or self.already_absent


@dataclass(frozen=True)
class ProjectBulkPurgeResult:
    """Best-effort permanent purge across several projects."""

    items: tuple[ProjectPurgeItemResult, ...]

    @property
    def requested_ids(self) -> tuple[str, ...]:
        return tuple(item.project_id for item in self.items)

    @property
    def deleted_ids(self) -> tuple[str, ...]:
        return tuple(item.project_id for item in self.items if item.deleted_or_absent)

    @property
    def incomplete_ids(self) -> tuple[str, ...]:
        return tuple(item.project_id for item in self.items if not item.complete)

    @property
    def complete(self) -> bool:
        return bool(self.items) and not self.incomplete_ids


__all__ = [
    "ProjectBulkMutationFailure",
    "ProjectBulkMutationResult",
    "ProjectBulkPurgeResult",
    "ProjectFolderOption",
    "ProjectListResult",
    "ProjectPurgeItemResult",
]
