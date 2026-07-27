"""Normalized project ownership and folder metadata.

The values in this module are organizational labels only. They do not grant
access and must not be confused with authenticated Supabase users or RLS.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

PROJECT_OWNER_SLUGS = ("unassigned", "dennis", "vipin", "christer", "shared")
PROJECT_ACTOR_SLUGS = ("dennis", "vipin", "christer")
PROJECT_OWNER_LABELS = {
    "unassigned": "Unassigned",
    "dennis": "Dennis",
    "vipin": "Vipin",
    "christer": "Christer",
    "shared": "Shared",
}
MAX_PROJECT_FOLDER_LENGTH = 80


@dataclass(frozen=True)
class ProjectOrganization:
    """Validated organizational metadata for one saved project."""

    owner_slug: str = "unassigned"
    folder_name: str = ""
    actor_slug: str = "unassigned"

    @classmethod
    def from_values(
        cls,
        *,
        owner_slug: object = "unassigned",
        folder_name: object = "",
        actor_slug: object = "unassigned",
    ) -> "ProjectOrganization":
        return cls(
            owner_slug=normalize_project_owner(owner_slug),
            folder_name=normalize_project_folder(folder_name),
            actor_slug=normalize_project_actor(actor_slug),
        )


def project_organization_from_metadata(
    metadata: Mapping[str, object] | None,
) -> ProjectOrganization | None:
    """Return organization data only when a saved payload explicitly owns it."""

    if not isinstance(metadata, Mapping):
        return None
    owned_keys = {"owner_slug", "folder_name", "created_by", "updated_by"}
    if not owned_keys.intersection(metadata):
        return None
    actor = metadata.get("updated_by") or metadata.get("created_by") or "unassigned"
    return ProjectOrganization.from_values(
        owner_slug=metadata.get("owner_slug") or "unassigned",
        folder_name=metadata.get("folder_name") or "",
        actor_slug=actor,
    )


def normalize_project_owner(value: object) -> str:
    """Return one supported owner slug."""

    clean = _owner_slug(value)
    if clean not in PROJECT_OWNER_SLUGS:
        labels = ", ".join(PROJECT_OWNER_LABELS[item] for item in PROJECT_OWNER_SLUGS)
        raise ValueError(f"Project owner must be one of: {labels}.")
    return clean


def normalize_project_actor(value: object) -> str:
    """Return one supported actor slug for audit metadata."""

    return normalize_project_owner(value)


def normalize_project_folder(value: object) -> str:
    """Return a compact logical folder/reference name, not a filesystem path."""

    clean = " ".join(str(value or "").split())
    if len(clean) > MAX_PROJECT_FOLDER_LENGTH:
        raise ValueError(f"Project folders must be {MAX_PROJECT_FOLDER_LENGTH} characters or fewer.")
    if any(character in clean for character in ("/", "\\")):
        raise ValueError("Project folders cannot contain slash characters.")
    if any(ord(character) < 32 for character in clean):
        raise ValueError("Project folders cannot contain control characters.")
    unsupported = [
        character
        for character in clean
        if not (character.isalnum() or character in " -_&'")
    ]
    if unsupported:
        raise ValueError("Project folders may use letters, numbers, spaces, hyphens and underscores.")
    return clean


def project_owner_label(value: object) -> str:
    """Return the user-facing label for an owner slug."""

    return PROJECT_OWNER_LABELS[normalize_project_owner(value)]


def _owner_slug(value: object) -> str:
    clean = " ".join(str(value or "").split()).casefold()
    return clean or "unassigned"


__all__ = [
    "MAX_PROJECT_FOLDER_LENGTH",
    "PROJECT_ACTOR_SLUGS",
    "PROJECT_OWNER_LABELS",
    "PROJECT_OWNER_SLUGS",
    "ProjectOrganization",
    "normalize_project_actor",
    "normalize_project_folder",
    "normalize_project_owner",
    "project_organization_from_metadata",
    "project_owner_label",
]
