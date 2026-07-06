from __future__ import annotations

from app_modules.project_identity import (
    active_project_id_from_state,
    clear_active_project_id,
    ensure_active_project_id,
    project_payload_with_id,
    set_active_project_id,
)
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_serialization import saved_project_to_dict
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import make_output_edit_state


def _rows() -> list[dict]:
    return [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Fjord Cruise",
            "client_description": "Generated supplier description",
            "row_id": "row-1",
            "line_number": 1,
            "date": "01/01/2027",
            "start_date": "01/01/2027",
        }
    ]


def _saved_project_payload(*, project_id: str = "project-id", itinerary_name: str = "Norway") -> dict:
    rows = _rows()
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    project = build_saved_project_from_state(
        {
            "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
            "raw_text_input": "Day 1\tActivity\tOslo Fjord Cruise",
            "parsed_rows": rows,
            "output_edits": edits,
            "detail_level": "Rich descriptive",
            "day_page_layout": "One day per page",
        },
        itinerary_name=itinerary_name,
        project_id=project_id,
    )
    return saved_project_to_dict(project)


def test_active_project_id_syncs_current_and_legacy_keys() -> None:
    state = {"active_saved_project_id": " legacy-id "}

    assert ensure_active_project_id(state) == "legacy-id"

    assert state["active_project_storage_id"] == "legacy-id"
    assert state["active_saved_project_id"] == "legacy-id"
    assert active_project_id_from_state(state) == "legacy-id"


def test_set_active_project_id_updates_saved_project_payload_metadata() -> None:
    state = {
        "active_saved_project": {
            "metadata": {"project_id": "old-id", "itinerary_name": "Norway"},
            "kind": "booknordics_saved_itinerary_project",
        }
    }

    set_active_project_id(state, "cloud-id")

    assert state["active_project_storage_id"] == "cloud-id"
    assert state["active_saved_project_id"] == "cloud-id"
    assert state["active_saved_project"]["metadata"]["project_id"] == "cloud-id"


def test_clear_active_project_id_keeps_project_payload_until_caller_removes_it() -> None:
    state = {
        "active_project_storage_id": "project-id",
        "active_saved_project_id": "project-id",
        "active_saved_project": {"metadata": {"project_id": "project-id"}},
    }

    clear_active_project_id(state)

    assert "active_project_storage_id" not in state
    assert "active_saved_project_id" not in state
    assert "active_saved_project" in state


def test_project_payload_with_id_does_not_mutate_original_payload() -> None:
    payload = {"metadata": {"project_id": "old-id", "itinerary_name": "Norway"}}

    updated = project_payload_with_id(payload, "new-id")

    assert updated["metadata"]["project_id"] == "new-id"
    assert payload["metadata"]["project_id"] == "old-id"


def test_load_saved_cloud_project_can_override_stale_payload_project_id() -> None:
    payload = _saved_project_payload(project_id="stale-id", itinerary_name="Norway")
    state = {}

    result = load_saved_project(state, payload, project_id_override="cloud-row-id")

    assert result.ok
    assert state["active_project_storage_id"] == "cloud-row-id"
    assert state["active_saved_project_id"] == "cloud-row-id"
    assert state["active_saved_project"]["metadata"]["project_id"] == "cloud-row-id"
