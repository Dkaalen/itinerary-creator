from __future__ import annotations

from pathlib import Path

from app_modules.calculator_download_action import prepare_calculation_download
from app_modules.calculator_navigation import (
    CALCULATOR_PAGE,
    WORKFLOW_PAGE,
    calculator_page_is_active,
    close_calculator_page,
    open_calculator_page,
)
from app_modules.calculator_grid_data import rows_to_table_data, table_data_to_rows
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def test_calculator_navigation_sets_standalone_page_without_changing_workflow_stage() -> None:
    state = {"app_stage": "input", "itinerary_name": "Tromso"}

    open_calculator_page(state)

    assert state["active_app_page"] == CALCULATOR_PAGE
    assert state["app_stage"] == "input"
    assert calculator_page_is_active(state) is True
    assert state["calculator_state"].itinerary_name == "Tromso"
    assert len(state["calculator_state"].rows) == 1

    close_calculator_page(state)

    assert state["active_app_page"] == WORKFLOW_PAGE
    assert calculator_page_is_active(state) is False


def test_calculator_table_round_trip_preserves_hidden_advanced_fields() -> None:
    source_row = CalculatorRow(
        row_id="1",
        day="Day 1",
        type="Hotel",
        supplier="Hidden supplier",
        comments="Hidden comment",
        gross_price_per_unit=100,
        units=2,
    )
    table_data = rows_to_table_data((source_row,), show_advanced=False)
    table_data[0]["travel_element"] = "Edited hotel"
    table_data[0]["gross_price_per_unit"] = "150"

    rows = table_data_to_rows(table_data, (source_row,))

    assert rows[0].travel_element == "Edited hotel"
    assert rows[0].gross_price_per_unit == 150
    assert rows[0].supplier == "Hidden supplier"
    assert rows[0].comments == "Hidden comment"


def test_calculator_download_action_returns_xlsx_payload() -> None:
    state = CalculatorState(
        itinerary_name="Tromsø Northern Lights 2026",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Activity",
                travel_element="Northern lights chase",
                gross_price_per_unit=1000,
                units=2,
                supplier_currency="NOK",
                sales_currency="NOK",
            ),
        ),
    )

    export = prepare_calculation_download(state)

    assert export.filename == "Tromsø Northern Lights 2026 - Calculation.xlsx"
    assert export.content.startswith(b"PK")


def test_calculator_keeps_main_workflow_contract_locked() -> None:
    config_source = Path("app_modules/workflow_config.py").read_text(encoding="utf-8")
    input_source = Path("app_modules/input_step.py").read_text(encoding="utf-8")
    main_view_source = Path("app_modules/main_view.py").read_text(encoding="utf-8")

    assert 'FLOW_STAGES = ("input", "edit", "pictures", "export")' in config_source
    assert "render_calculator_entry_button" in input_source
    assert "calculator_page_is_active" in main_view_source
