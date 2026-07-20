from __future__ import annotations

from app_modules.calculator_backup_action import CalculatorUploadImport
from app_modules.calculator_open_action import apply_calculator_upload_import
from app_modules.calculator_state_keys import (
    CALCULATOR_RETURN_AVAILABLE_KEY,
    CALCULATOR_STATE_KEY,
    CURRENCY_RATES_STATE_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def test_opening_local_excel_detaches_previous_cloud_project() -> None:
    imported_state = CalculatorState(
        itinerary_name="Imported Excel",
        rows=(CalculatorRow(row_id="1", travel_element="Imported hotel"),),
    )
    session_state = {
        "active_saved_project_id": "cloud-project-1",
        "active_project_storage_id": "cloud-project-1",
        "active_saved_project": {"metadata": {"project_id": "cloud-project-1"}},
        "project_storage_last_saved_snapshot_path": "saved/project.json",
        CALCULATOR_RETURN_AVAILABLE_KEY: True,
        CALCULATOR_STATE_KEY: CalculatorState(
            itinerary_name="Cloud project",
            rows=(CalculatorRow(row_id="1", travel_element="Old hotel"),),
        ),
    }

    notice = apply_calculator_upload_import(
        session_state,
        CalculatorUploadImport(
            state=imported_state,
            currency_rates={"NOK": 1.0, "EUR": 11.0},
            source="xlsx",
        ),
        filename="Imported Excel.xlsx",
    )

    assert notice.level == "success"
    assert notice.message == "Opened Imported Excel.xlsx."
    assert session_state[CALCULATOR_STATE_KEY] == imported_state
    assert session_state[CURRENCY_RATES_STATE_KEY] == {"NOK": 1.0, "EUR": 11.0}
    assert session_state["calculator_currency_rate_EUR"] == 11.0
    assert "active_saved_project_id" not in session_state
    assert "active_project_storage_id" not in session_state
    assert "active_saved_project" not in session_state
    assert "project_storage_last_saved_snapshot_path" not in session_state
    assert CALCULATOR_RETURN_AVAILABLE_KEY not in session_state


def test_open_notice_reports_import_warnings_without_rejecting_valid_rows() -> None:
    imported_state = CalculatorState(
        itinerary_name="Imported Excel",
        rows=(CalculatorRow(row_id="1", travel_element="Imported transfer"),),
    )

    notice = apply_calculator_upload_import(
        {},
        CalculatorUploadImport(
            state=imported_state,
            warnings=("Row 8 had an unsupported note", "Row 9 used a cached value"),
            source="xlsx",
        ),
        filename="Warnings.xlsx",
    )

    assert notice.level == "warning"
    assert "Row 8 had an unsupported note" in notice.message
    assert "Row 9 used a cached value" in notice.message
