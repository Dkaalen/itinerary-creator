"""Capability model for optional Project Explorer Supabase schema features."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectStorageCapabilities:
    """Schema features detected once for one repository session."""

    management_schema: bool
    folder_listing: bool
    reason: str = ""

    @property
    def organization_controls(self) -> bool:
        return self.management_schema

    @property
    def folder_filter(self) -> bool:
        return self.management_schema and self.folder_listing

    @classmethod
    def legacy(cls, reason: str = "migration_required") -> "ProjectStorageCapabilities":
        return cls(management_schema=False, folder_listing=False, reason=reason)

    @classmethod
    def management_only(cls, reason: str = "folder_rpc_unavailable") -> "ProjectStorageCapabilities":
        return cls(management_schema=True, folder_listing=False, reason=reason)

    @classmethod
    def full(cls) -> "ProjectStorageCapabilities":
        return cls(management_schema=True, folder_listing=True)


__all__ = ["ProjectStorageCapabilities"]
