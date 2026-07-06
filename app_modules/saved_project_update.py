"""Update saved projects from the current editable workflow state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from app_modules.saved_project_builder import Clock, build_saved_project_snapshot_from_state
from app_modules.saved_project_calculator_state import calculator_snapshot_from_workflow_state
from app_modules.saved_project_cleaning import clean_output_edits
from app_modules.saved_project_export_state import export_state_from_workflow_state
from app_modules.saved_project_image_state import image_state_from_output_edits
from app_modules.saved_project_model import SavedItineraryProject


def update_saved_project_current_snapshot(
    project: SavedItineraryProject,
    state: Mapping[str, Any],
    *,
    clock: Clock | None = None,
) -> SavedItineraryProject:
    """Return ``project`` with its current snapshot replaced from workflow state."""

    snapshot = build_saved_project_snapshot_from_state(state, clock=clock)
    output_edits = clean_output_edits(state.get("output_edits", {}))
    output_brand = str(output_edits.get("output_brand") or project.output_brand or project.mode or "agent")
    return replace(
        project,
        metadata=replace(project.metadata, updated_at=snapshot.created_at),
        current_snapshot=snapshot,
        image_state=image_state_from_output_edits(output_edits),
        export_state=export_state_from_workflow_state(
            state,
            saved_at=snapshot.created_at,
            previous=project.export_state,
        ),
        output_brand=output_brand,
        mode=output_brand,
        calculator_snapshot=calculator_snapshot_from_workflow_state(state),
    )
