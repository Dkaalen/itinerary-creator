"""Prepare downloadable saved-project files from workflow state."""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.project_identity import active_project_id_from_state, set_active_project_id
from app_modules.saved_project_builder import Clock, build_saved_project_from_state
from app_modules.saved_project_model import SavedItineraryProject
from app_modules.saved_project_current_state import active_saved_project_from_state
from app_modules.saved_project_serialization import saved_project_to_dict, saved_project_to_json
from app_modules.saved_project_storage_decision import assert_project_file_mode_payload
from app_modules.saved_project_update import update_saved_project_current_snapshot
from app_modules.saved_project_validation import SavedProjectError

PROJECT_FILE_MIME = "application/json"
PROJECT_FILE_SUFFIX = ".itinerary.json"
DEFAULT_PROJECT_FILE_STEM = "saved_itinerary_project"


@dataclass(frozen=True)
class SavedProjectFileDownload:
    file_name: str
    data: bytes
    payload: dict[str, Any]


def prepare_saved_project_file_download(
    state: MutableMapping[str, Any],
    *,
    itinerary_name: str | None = None,
    clock: Clock | None = None,
) -> SavedProjectFileDownload:
    """Return a validated saved-project JSON download for the current itinerary."""

    _require_generated_project(state)
    project = active_saved_project_from_state(state)
    if project is None:
        project = build_saved_project_from_state(
            state,
            itinerary_name=str(itinerary_name if itinerary_name is not None else state.get("itinerary_name") or ""),
            project_id=active_project_id_from_state(state) or None,
            clock=clock,
        )
    else:
        project = update_saved_project_current_snapshot(project, state, clock=clock)

    payload = saved_project_to_dict(project)
    assert_project_file_mode_payload(payload)
    state["active_saved_project"] = payload
    set_active_project_id(state, project.metadata.project_id)
    state["itinerary_name"] = project.metadata.itinerary_name

    return SavedProjectFileDownload(
        file_name=project_file_name(project),
        data=saved_project_to_json(project).encode("utf-8"),
        payload=payload,
    )


def project_file_name(project: SavedItineraryProject) -> str:
    """Return a safe browser download filename for a saved project."""

    snapshot_edits = project.current_snapshot.output_edits if project.current_snapshot else {}
    title = project.metadata.itinerary_name or str(snapshot_edits.get("trip_title") or "")
    slug = _filename_stem(title)
    return f"{slug}{PROJECT_FILE_SUFFIX}"


def _require_generated_project(state: Mapping[str, Any]) -> None:
    if not state.get("parsed_rows") or not isinstance(state.get("output_edits"), Mapping) or not state.get("output_edits"):
        raise SavedProjectError("Generate an itinerary before saving a project file.")


def _filename_stem(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._ -]+", "", str(value or "")).strip().lower()
    normalized = re.sub(r"[\s._-]+", "_", normalized).strip("_")
    return normalized[:80] or DEFAULT_PROJECT_FILE_STEM
