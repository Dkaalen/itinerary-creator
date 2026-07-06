"""Typed result for cloud project deletion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectDeleteResult:
    """Outcome of deleting a project row and its registered storage files."""

    itinerary_id: str
    storage_paths: tuple[str, ...] = ()
    record_deleted: bool = False
    storage_files_deleted: bool = True
    storage_error: str = ""

    @property
    def ok(self) -> bool:
        """Return whether the itinerary record itself was deleted."""

        return self.record_deleted

    @property
    def complete(self) -> bool:
        """Return whether the record and best-effort storage cleanup both succeeded."""

        return self.record_deleted and self.storage_files_deleted
