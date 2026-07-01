"""Validation rules for saved itinerary project payloads."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app_modules.saved_project_constants import (
    BANNED_RECURSIVE_KEYS,
    BANNED_SESSION_KEYS,
    SAVED_PROJECT_KIND,
    SAVED_PROJECT_MAX_BYTES,
    SAVED_PROJECT_SCHEMA_VERSION,
    SUPPORTED_PROJECT_STATUSES,
)


class SavedProjectError(ValueError):
    """Raised when a saved-project payload cannot be used safely."""


REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "saved_schema_version",
        "kind",
        "metadata",
        "source",
        "generated_baseline_snapshot",
        "current_snapshot",
        "image_state",
        "export_state",
        "output_brand",
        "mode",
    }
)

REQUIRED_METADATA_KEYS = frozenset({"project_id", "itinerary_name", "created_at", "updated_at", "status"})
REQUIRED_SOURCE_KEYS = frozenset({"source_input", "source_hash"})
REQUIRED_SNAPSHOT_KEYS = frozenset({"snapshot_id", "created_at", "parsed_rows", "output_edits", "detail_level", "day_page_layout"})
REQUIRED_IMAGE_KEYS = frozenset({"cover_image", "summary_image", "day_images", "pictures_added"})
REQUIRED_EXPORT_KEYS = frozenset({"pdf_status", "last_exported_at"})


def validate_saved_project_payload(payload: Mapping[str, Any], *, max_bytes: int = SAVED_PROJECT_MAX_BYTES) -> None:
    """Raise SavedProjectError when a project payload violates the contract."""

    if not isinstance(payload, Mapping):
        raise SavedProjectError("Saved project must be a JSON object.")
    _enforce_payload_size(payload, max_bytes=max_bytes)
    _require_keys(payload, REQUIRED_TOP_LEVEL_KEYS, "project")

    if payload.get("saved_schema_version") != SAVED_PROJECT_SCHEMA_VERSION:
        raise SavedProjectError(f"Unsupported saved project schema version: {payload.get('saved_schema_version')!r}.")
    if payload.get("kind") != SAVED_PROJECT_KIND:
        raise SavedProjectError("This file is not a saved itinerary project.")

    metadata = _mapping(payload.get("metadata"), "metadata")
    source = _mapping(payload.get("source"), "source")
    baseline = _mapping(payload.get("generated_baseline_snapshot"), "generated_baseline_snapshot")
    current = _mapping(payload.get("current_snapshot"), "current_snapshot")
    image_state = _mapping(payload.get("image_state"), "image_state")
    export_state = _mapping(payload.get("export_state"), "export_state")

    _require_keys(metadata, REQUIRED_METADATA_KEYS, "metadata")
    _require_keys(source, REQUIRED_SOURCE_KEYS, "source")
    _require_keys(baseline, REQUIRED_SNAPSHOT_KEYS, "generated_baseline_snapshot")
    _require_keys(current, REQUIRED_SNAPSHOT_KEYS, "current_snapshot")
    _require_keys(image_state, REQUIRED_IMAGE_KEYS, "image_state")
    _require_keys(export_state, REQUIRED_EXPORT_KEYS, "export_state")

    if not str(metadata.get("project_id") or "").strip():
        raise SavedProjectError("Saved project project_id is required.")
    if str(metadata.get("status") or "") not in SUPPORTED_PROJECT_STATUSES:
        raise SavedProjectError("Saved project status is not supported.")
    _validate_source_hash(source)
    _validate_snapshot_identity(baseline, "generated_baseline_snapshot")
    _validate_snapshot_identity(current, "current_snapshot")
    if not isinstance(baseline.get("parsed_rows"), list) or not isinstance(current.get("parsed_rows"), list):
        raise SavedProjectError("Saved project snapshots must contain parsed row lists.")
    if not isinstance(baseline.get("output_edits"), Mapping) or not isinstance(current.get("output_edits"), Mapping):
        raise SavedProjectError("Saved project snapshots must contain output edit objects.")

    banned = tuple(_banned_key_paths(payload))
    if banned:
        raise SavedProjectError(f"Saved project contains temporary or preview-only fields: {', '.join(banned[:5])}.")


def _require_keys(payload: Mapping[str, Any], required: frozenset[str], label: str) -> None:
    missing = sorted(key for key in required if key not in payload)
    if missing:
        raise SavedProjectError(f"Saved project {label} is missing required fields: {', '.join(missing)}.")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SavedProjectError(f"Saved project {label} must be an object.")
    return value


def _enforce_payload_size(payload: Mapping[str, Any], *, max_bytes: int) -> None:
    try:
        size = len(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    except TypeError as error:
        raise SavedProjectError("Saved project payload is not JSON serializable.") from error
    if size > max_bytes:
        raise SavedProjectError(f"Saved project payload is too large: {size} bytes.")


def _banned_key_paths(value: Any, *, path: str = "") -> tuple[str, ...]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text in BANNED_SESSION_KEYS or key_text in BANNED_RECURSIVE_KEYS:
                hits.append(child_path)
            hits.extend(_banned_key_paths(item, path=child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_banned_key_paths(item, path=f"{path}[{index}]"))
    return tuple(hits)


def _validate_source_hash(source: Mapping[str, Any]) -> None:
    source_input = str(source.get("source_input") or "")
    expected_hash = hashlib.sha256(source_input.encode("utf-8")).hexdigest()
    if source.get("source_hash") != expected_hash:
        raise SavedProjectError("Saved project source hash does not match the saved source input.")


def _validate_snapshot_identity(snapshot: Mapping[str, Any], label: str) -> None:
    if not str(snapshot.get("snapshot_id") or "").strip():
        raise SavedProjectError(f"Saved project {label} snapshot_id is required.")
    if not str(snapshot.get("created_at") or "").strip():
        raise SavedProjectError(f"Saved project {label} created_at is required.")
