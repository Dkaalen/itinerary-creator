from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import streamlit as st

from app_modules.project_io import (
    cancel_pending_project_json_import,
    confirm_pending_project_json_import,
    pending_project_json_import,
    request_project_json_import,
)
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_serialization import saved_project_to_dict
from itinerary_generation.common import group_rows_by_day
from tests.support.static_contracts import read_contract_text
from tests.support.streamlit_stub import SessionState
from ui.output_edits import make_output_edit_state


def test_calculator_prepares_then_downloads_excel_from_the_grid_toolbar() -> None:
    action_source = read_contract_text("app_modules/calculator_download_action.py")
    actions_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_actions.js")
    excel_actions_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_excel_actions.js")
    toolbar_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_toolbar_render.js")
    page_source = read_contract_text("app_modules/calculator_page.py")

    assert "prepare_staged_calculation_download" in action_source
    assert "ready_calculation_download_payload" in action_source
    assert '"content_base64"' in action_source
    assert '"content": export.content' not in action_source
    assert "saved_to_cloud" not in action_source
    assert "render_ready_calculation_download" not in action_source
    assert "auto_download" not in action_source
    assert "auto_download" not in actions_source
    assert "downloadPreparedExcel" in actions_source
    assert "anchor.click()" in excel_actions_source
    assert "pending_download=pending_download" in page_source
    assert "Excel ready" in toolbar_source


def test_open_project_manager_is_full_width_selectable_and_loads_files_only_for_selection() -> None:
    input_source = read_contract_text("app_modules/input_step.py")
    ui_source = read_contract_text("app_modules/project_browser_ui.py")
    controls_source = read_contract_text("app_modules/project_browser_controls.py")
    list_source = read_contract_text("app_modules/project_browser_list_ui.py")
    detail_source = read_contract_text("app_modules/project_browser_detail_ui.py")
    bulk_source = read_contract_text("app_modules/project_browser_bulk_ui.py")
    calculator_file_source = read_contract_text("app_modules/project_browser_calculation_files.py")
    from ui import style_app_shell

    css = style_app_shell.CSS

    assert "Search" in controls_source
    assert "Recently saved" in controls_source
    assert "Newest created" in controls_source
    assert "Working as" not in controls_source
    assert "Owner" in controls_source
    assert "Manage multiple projects" not in controls_source
    assert "list_cloud_project_explorer_page" in ui_source
    assert 'st.container(border=True, key="cloud_project_explorer")' in ui_source
    assert "render_project_table(" in ui_source
    assert "render_selected_project_panel(selected, query=query)" in ui_source
    assert "render_open_project_workspace_if_visible()" in input_source
    assert input_source.index("render_open_project_workspace_if_visible()") > input_source.index("with project_col:")
    assert 'st.dataframe(' in list_source
    assert 'height=PROJECT_TABLE_HEIGHT' in list_source
    assert 'on_select="rerun"' in list_source
    assert 'selection_mode="multi-row"' in list_source
    assert "st.popover" not in list_source
    assert "render_calculation_files" not in list_source
    assert detail_source.count("render_calculation_files(project_id)") == 1
    assert "Save as copy" in detail_source
    assert "Delete" in detail_source
    assert "Delete permanently" not in detail_source
    assert "Change owner" in bulk_source
    assert "Move to folder/reference" in bulk_source
    assert "Restore" not in bulk_source
    assert "Delete projects" in bulk_source
    assert "Delete permanently" in bulk_source
    assert "Prepare calculator file" in calculator_file_source
    assert "Download calculator file" in calculator_file_source
    assert "Delete file permanently" in calculator_file_source
    assert "list_cloud_calculation_files" in calculator_file_source
    assert calculator_file_source.index("if not visible:") < calculator_file_source.index(
        "files = list_cloud_calculation_files"
    )
    assert "@st.dialog" not in ui_source
    assert "OPEN_PROJECT_BROWSER_VISIBLE_KEY" in ui_source
    assert ".st-key-cloud_project_explorer" in css
    assert '[data-testid="stDataFrame"]' in css
    assert ".cloud-project-selected-strip" in css
    assert "Open a backup file" in ui_source


class _NamedBytesIO(io.BytesIO):
    name = "replacement.itinerary.json"


def _saved_backup_payload(title: str = "Replacement cruise") -> bytes:
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": title,
            "client_description": title,
            "row_id": "row-1",
            "line_number": 1,
            "date": "01/01/2027",
            "start_date": "01/01/2027",
        }
    ]
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    state = {
        "last_generated_raw_text": f"Day 1\tActivity\t{title}",
        "raw_text_input": f"Day 1\tActivity\t{title}",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
    }
    project = build_saved_project_from_state(
        state,
        itinerary_name="Replacement itinerary",
        clock=lambda: datetime(2026, 7, 22, tzinfo=timezone.utc),
    )
    return json.dumps(saved_project_to_dict(project)).encode("utf-8")


def test_backup_open_is_staged_before_replacing_detached_supplier_text() -> None:
    st.session_state = SessionState({"raw_text_input": "Unsaved supplier rows"})

    opened = request_project_json_import(_NamedBytesIO(_saved_backup_payload()), require_saved_project=True)

    assert opened is None
    assert st.session_state["raw_text_input"] == "Unsaved supplier rows"
    pending = pending_project_json_import()
    assert pending is not None
    assert pending.filename == "replacement.itinerary.json"


def test_confirmed_backup_open_replaces_workspace_under_fresh_identity(monkeypatch) -> None:
    st.session_state = SessionState({"raw_text_input": "Unsaved supplier rows"})
    monkeypatch.setattr("app_modules.project_io.uuid4", lambda: "fresh-backup-project")
    request_project_json_import(_NamedBytesIO(_saved_backup_payload()), require_saved_project=True)

    assert confirm_pending_project_json_import() is True

    assert st.session_state["active_saved_project_id"] == "fresh-backup-project"
    assert st.session_state["parsed_rows"][0]["title"] == "Replacement cruise"
    assert pending_project_json_import() is None


def test_cancelled_backup_open_preserves_current_workspace() -> None:
    st.session_state = SessionState({"raw_text_input": "Unsaved supplier rows"})
    request_project_json_import(_NamedBytesIO(_saved_backup_payload()), require_saved_project=True)

    cancel_pending_project_json_import()

    assert st.session_state["raw_text_input"] == "Unsaved supplier rows"
    assert pending_project_json_import() is None
    assert "active_saved_project_id" not in st.session_state


def test_clean_workspace_opens_backup_without_confirmation(monkeypatch) -> None:
    st.session_state = SessionState()
    monkeypatch.setattr("app_modules.project_io.uuid4", lambda: "clean-open-project")

    opened = request_project_json_import(_NamedBytesIO(_saved_backup_payload()), require_saved_project=True)

    assert opened is True
    assert pending_project_json_import() is None
    assert st.session_state["active_saved_project_id"] == "clean-open-project"


def test_invalid_backup_is_rejected_before_confirmation() -> None:
    st.session_state = SessionState({"raw_text_input": "Unsaved supplier rows"})

    opened = request_project_json_import(_NamedBytesIO(b"not-json"), require_saved_project=True)

    assert opened is False
    assert pending_project_json_import() is None
    assert st.session_state["raw_text_input"] == "Unsaved supplier rows"


def test_invalid_saved_project_schema_is_rejected_before_confirmation() -> None:
    st.session_state = SessionState({"raw_text_input": "Unsaved supplier rows"})
    payload = json.loads(_saved_backup_payload())
    payload["saved_schema_version"] = 999

    opened = request_project_json_import(
        _NamedBytesIO(json.dumps(payload).encode("utf-8")),
        require_saved_project=True,
    )

    assert opened is False
    assert pending_project_json_import() is None
    assert st.session_state["raw_text_input"] == "Unsaved supplier rows"


def test_unsaved_detection_includes_generated_workflow_edits() -> None:
    payload = json.loads(_saved_backup_payload())
    state = SessionState(
        {
            "active_saved_project": payload,
            "project_storage_last_saved_baseline": payload,
            "itinerary_name": "Replacement itinerary",
            "raw_text_input": payload["source"]["source_input"],
            "parsed_rows": payload["current_snapshot"]["parsed_rows"],
            "output_edits": payload["current_snapshot"]["output_edits"],
            "detail_level": payload["current_snapshot"]["detail_level"],
            "day_page_layout": payload["current_snapshot"]["day_page_layout"],
        }
    )
    assert active_project_has_unsaved_changes(state) is False

    state["output_edits"] = dict(state["output_edits"])
    state["output_edits"]["trip_title"] = "Edited but not saved"

    assert active_project_has_unsaved_changes(state) is True
