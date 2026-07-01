"""Explicit baseline-restore helper for saved itinerary projects."""

from __future__ import annotations

import uuid
from dataclasses import replace

from app_modules.saved_project_builder import Clock, _timestamp
from app_modules.saved_project_cleaning import clean_output_edits
from app_modules.saved_project_image_state import image_state_from_output_edits
from app_modules.saved_project_model import SavedItineraryProject, SavedProjectExportState


class SavedProjectBaselineRestoreError(ValueError):
    """Raised when baseline restore is requested without an explicit confirmation."""


def restore_baseline_snapshot_as_current(
    project: SavedItineraryProject,
    *,
    confirm_replace_current: bool = False,
    clock: Clock | None = None,
) -> SavedItineraryProject:
    """Return ``project`` with its generated baseline copied into current state.

    This helper is intentionally not wired to any visible UI in Patch 47. It
    exists to make future baseline-restore behavior explicit and testable so a
    saved project's edited current snapshot cannot be overwritten silently.
    """

    if not confirm_replace_current:
        raise SavedProjectBaselineRestoreError(
            "Restoring the generated baseline requires explicit confirmation because it replaces the current edited version."
        )

    restored_at = _timestamp(clock)
    baseline = project.generated_baseline_snapshot
    current_snapshot = replace(
        baseline,
        snapshot_id=uuid.uuid4().hex,
        created_at=restored_at,
    )
    output_edits = clean_output_edits(current_snapshot.output_edits)
    output_brand = str(output_edits.get("output_brand") or project.output_brand or project.mode or "agent")

    return replace(
        project,
        metadata=replace(project.metadata, updated_at=restored_at),
        current_snapshot=current_snapshot,
        image_state=image_state_from_output_edits(output_edits),
        export_state=SavedProjectExportState(
            pdf_status="Needs refresh",
            last_exported_at=project.export_state.last_exported_at,
        ),
        output_brand=output_brand,
        mode=output_brand,
    )
