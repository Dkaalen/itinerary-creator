"""Build saved-project contracts from current workflow state."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable

from app_modules.saved_project_calculator_state import calculator_snapshot_from_workflow_state
from app_modules.saved_project_cleaning import clean_output_edits, clean_parsed_rows
from app_modules.saved_project_export_state import export_state_from_workflow_state
from app_modules.saved_project_image_state import image_state_from_output_edits
from app_modules.saved_project_constants import ACTIVE_PROJECT_STATUS, SAVED_PROJECT_KIND, SAVED_PROJECT_SCHEMA_VERSION
from app_modules.saved_project_model import (
    SavedItineraryProject,
    SavedItinerarySnapshot,
    SavedProjectMetadata,
    SavedProjectSource,
)
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT

Clock = Callable[[], datetime]


def build_saved_project_from_state(
    state: Mapping[str, Any],
    *,
    itinerary_name: str = "",
    project_id: str | None = None,
    clock: Clock | None = None,
) -> SavedItineraryProject:
    """Create a versioned saved-project object from generated workflow state."""

    now = _timestamp(clock)
    resolved_project_id = project_id or uuid.uuid4().hex
    output_edits = clean_output_edits(state.get("output_edits", {}))
    snapshot = build_saved_project_snapshot_from_state(state, created_at=now)
    output_brand = str(output_edits.get("output_brand") or state.get("output_brand") or "agent")
    source_input = str(state.get("last_generated_raw_text") or state.get("raw_text_input") or "")

    return SavedItineraryProject(
        saved_schema_version=SAVED_PROJECT_SCHEMA_VERSION,
        kind=SAVED_PROJECT_KIND,
        metadata=SavedProjectMetadata(
            project_id=resolved_project_id,
            itinerary_name=str(itinerary_name or ""),
            created_at=now,
            updated_at=now,
            status=ACTIVE_PROJECT_STATUS,
        ),
        source=SavedProjectSource(
            source_input=source_input,
            source_hash=hash_source_input(source_input),
        ),
        generated_baseline_snapshot=snapshot,
        current_snapshot=snapshot,
        image_state=image_state_from_output_edits(output_edits),
        export_state=export_state_from_workflow_state(state, saved_at=now),
        output_brand=output_brand,
        mode=output_brand,
        calculator_snapshot=calculator_snapshot_from_workflow_state(state),
    )


def hash_source_input(source_input: str) -> str:
    return hashlib.sha256(str(source_input or "").encode("utf-8")).hexdigest()


def _timestamp(clock: Clock | None) -> str:
    now = clock() if clock else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_saved_project_snapshot_from_state(
    state: Mapping[str, Any],
    *,
    created_at: str | None = None,
    clock: Clock | None = None,
) -> SavedItinerarySnapshot:
    """Create a durable saved-project snapshot from generated/editable state."""

    output_edits = clean_output_edits(state.get("output_edits", {}))
    parsed_rows = clean_parsed_rows(state.get("parsed_rows", []))
    timestamp = created_at or _timestamp(clock)
    return SavedItinerarySnapshot(
        snapshot_id=uuid.uuid4().hex,
        created_at=timestamp,
        parsed_rows=parsed_rows,
        output_edits=output_edits,
        detail_level=str(state.get("detail_level") or output_edits.get("detail_level") or "Rich descriptive"),
        day_page_layout=str(state.get("day_page_layout") or output_edits.get("day_page_layout") or DEFAULT_DAY_PAGE_LAYOUT),
    )
