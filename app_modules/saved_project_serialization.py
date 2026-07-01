"""Serialization helpers for saved itinerary project contracts."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from app_modules.saved_project_model import (
    SavedItineraryProject,
    SavedItinerarySnapshot,
    SavedProjectExportState,
    SavedProjectImageState,
    SavedProjectMetadata,
    SavedProjectSource,
)
from app_modules.saved_project_validation import validate_saved_project_payload


def saved_project_to_dict(project: SavedItineraryProject) -> dict[str, Any]:
    payload = asdict(project)
    validate_saved_project_payload(payload)
    return payload


def saved_project_to_json(project: SavedItineraryProject) -> str:
    return json.dumps(saved_project_to_dict(project), ensure_ascii=False, indent=2, sort_keys=True)


def saved_project_from_dict(payload: dict[str, Any]) -> SavedItineraryProject:
    validate_saved_project_payload(payload)
    return SavedItineraryProject(
        saved_schema_version=int(payload["saved_schema_version"]),
        kind=str(payload["kind"]),
        metadata=SavedProjectMetadata(**payload["metadata"]),
        source=SavedProjectSource(**payload["source"]),
        generated_baseline_snapshot=SavedItinerarySnapshot(**payload["generated_baseline_snapshot"]),
        current_snapshot=SavedItinerarySnapshot(**payload["current_snapshot"]),
        image_state=SavedProjectImageState(**payload["image_state"]),
        export_state=SavedProjectExportState(**payload["export_state"]),
        output_brand=str(payload.get("output_brand") or "agent"),
        mode=str(payload.get("mode") or "agent"),
    )


def saved_project_from_json(payload_json: str) -> SavedItineraryProject:
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("Saved project JSON must contain an object.")
    return saved_project_from_dict(payload)
