from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from app_modules.calculator_backup_action import CalculatorUploadImport
from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_open_action import apply_calculator_upload_import
from app_modules.calculator_session_state import apply_calculator_grid_result
from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY, CURRENCY_RATES_STATE_KEY
from app_modules.saved_project_builder import build_saved_project_from_state
from app_modules.saved_project_calculator_state import restore_calculator_snapshot_to_state
from app_modules.saved_project_load_action import load_saved_project
from app_modules.saved_project_serialization import saved_project_to_dict
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from itinerary_generation.common import group_rows_by_day
from ui.output_edits import make_output_edit_state


def _clock() -> datetime:
    return datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _calculator_state() -> CalculatorState:
    return CalculatorState(
        itinerary_name="Norway Restore",
        number_of_pax=4,
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Activity",
                travel_element="Oslo Fjord Cruise",
                gross_price_per_unit=100,
                units=4,
                supplier_currency="EUR",
            ),
        ),
    )


def _generated_state() -> dict:
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "Oslo Fjord Cruise",
            "client_description": "Generated description",
            "row_id": "row-1",
            "line_number": 1,
            "date": "01/09/2026",
            "start_date": "01/09/2026",
        }
    ]
    edits = make_output_edit_state(rows, group_rows_by_day(rows))
    edits["output_brand"] = "agent"
    edits["rows"]["row-1"]["title"] = "Saved edited cruise title"
    return {
        "last_generated_raw_text": "Day 1\tActivity\tOslo Fjord Cruise",
        "raw_text_input": "stale input",
        "parsed_rows": rows,
        "output_edits": edits,
        "detail_level": "Rich descriptive",
        "day_page_layout": "One day per page",
        CALCULATOR_STATE_KEY: _calculator_state(),
        CURRENCY_RATES_STATE_KEY: {"NOK": 1.0, "EUR": 11.4},
    }


def test_calculator_snapshot_import_and_browser_recovery_share_one_workspace_result() -> None:
    target = _calculator_state()

    saved_state: dict[str, object] = {
        "calculator_currency_rate_OLD": 99.0,
        CURRENCY_RATES_STATE_KEY: {"OLD": 99.0},
    }
    restore_calculator_snapshot_to_state(
        saved_state,
        {
            "itinerary_name": target.itinerary_name,
            "number_of_pax": target.number_of_pax,
            "rows": [row.__dict__ for row in target.rows],
            "currency_rates": {"NOK": 1.0, "EUR": 11.4},
        },
    )

    imported_state: dict[str, object] = {"calculator_currency_rate_OLD": 99.0}
    apply_calculator_upload_import(
        imported_state,
        CalculatorUploadImport(state=target, currency_rates={"NOK": 1.0, "EUR": 11.4}),
        filename="restore.xlsx",
    )

    recovered_state: dict[str, object] = {CURRENCY_RATES_STATE_KEY: {"NOK": 1.0, "EUR": 11.4}}
    apply_calculator_grid_result(
        recovered_state,
        CalculatorGridResult(action="sync", state=target, request_id="recovery-1"),
    )

    assert saved_state[CALCULATOR_STATE_KEY] == target
    assert imported_state[CALCULATOR_STATE_KEY] == target
    assert recovered_state[CALCULATOR_STATE_KEY] == target
    assert "calculator_currency_rate_OLD" not in saved_state
    assert "calculator_currency_rate_OLD" not in imported_state
    assert recovered_state[CURRENCY_RATES_STATE_KEY] == {"NOK": 1.0, "EUR": 11.4}


def test_saved_project_object_and_serialized_payload_reconstruct_equivalent_workflow_state() -> None:
    project = build_saved_project_from_state(
        _generated_state(),
        itinerary_name="Norway Restore",
        project_id="project-restore",
        clock=_clock,
    )
    payload = saved_project_to_dict(project)

    object_state: dict[str, object] = {}
    payload_state: dict[str, object] = {}
    assert load_saved_project(object_state, project).ok is True
    assert load_saved_project(payload_state, deepcopy(payload)).ok is True

    keys = (
        "parsed_rows",
        "output_edits",
        "raw_text_input",
        "itinerary_name",
        "app_stage",
        "preview_signature",
        CALCULATOR_STATE_KEY,
        CURRENCY_RATES_STATE_KEY,
    )
    for key in keys:
        assert payload_state[key] == object_state[key]


def test_current_snapshot_is_the_only_reopen_source_and_future_baseline_restore_module_is_removed() -> None:
    load_source = Path("app_modules/saved_project_load_action.py").read_text(encoding="utf-8")
    restore_source = Path("app_modules/saved_project_restore.py").read_text(encoding="utf-8")

    assert "current_snapshot" in load_source
    assert "generated_baseline_snapshot" not in load_source
    assert "generated_baseline_snapshot" not in restore_source
    assert not Path("app_modules/saved_project_baseline_restore.py").exists()


def test_restore_modules_keep_loading_and_state_application_separate() -> None:
    load_source = Path("app_modules/saved_project_load_action.py").read_text(encoding="utf-8")
    restore_source = Path("app_modules/saved_project_restore.py").read_text(encoding="utf-8")
    calculator_restore_source = Path("app_modules/calculator_restore.py").read_text(encoding="utf-8")

    assert "build_itinerary_html_from_context" not in load_source
    assert "save_html_file" not in load_source
    assert "restore_saved_project_to_state" in load_source
    assert "build_itinerary_html_from_context" not in restore_source
    assert "build_and_persist_itinerary_render_artifact" in restore_source
    assert "restore_calculator_snapshot_to_state" in restore_source
    assert "store_calculator_state" in calculator_restore_source
