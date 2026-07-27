"""Pure Save As payload preparation for a new stable project identity."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

IdFactory = Callable[[], str]
Clock = Callable[[], datetime]


def prepare_project_save_as_payload(
    project: Mapping[str, Any],
    *,
    new_name: object,
    id_factory: IdFactory = lambda: str(uuid4()),
    clock: Clock = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    """Return a detached project copy with fresh identity and timestamps."""

    name = normalize_project_name(new_name)
    payload = deepcopy(dict(project))
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    timestamp = _timestamp(clock())
    metadata.update(
        {
            "project_id": str(id_factory()).strip(),
            "itinerary_name": name,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )
    if not metadata["project_id"]:
        raise ValueError("A new project identity could not be created.")
    payload["metadata"] = metadata
    return payload


def normalize_project_name(value: object) -> str:
    """Validate one compact project display name."""

    name = " ".join(str(value or "").split())
    if not name:
        raise ValueError("Enter a project name before saving.")
    if len(name) > 160:
        raise ValueError("Project names must be 160 characters or fewer.")
    return name


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["normalize_project_name", "prepare_project_save_as_payload"]
