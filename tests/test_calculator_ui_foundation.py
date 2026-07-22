from __future__ import annotations

from pathlib import Path

from app_modules.calculator_download_action import prepare_calculation_download
from app_modules.calculator_navigation import (
    CALCULATOR_PAGE,
    WORKFLOW_PAGE,
    calculator_page_is_active,
    calculator_return_is_available,
    close_calculator_page,
    open_calculator_page,
)
from app_modules.calculator_grid_data import rows_to_table_data, table_data_to_rows
from app_modules.calculator_state_keys import CALCULATOR_RETURN_AVAILABLE_KEY
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def _calculator_js_source(*names: str) -> str:
    root = Path("calculator_grid_component/frontend/js")
    return "\n".join((root / name).read_text(encoding="utf-8") for name in names)


def _calculator_js_bundle_source() -> str:
    root = Path("calculator_grid_component/frontend/js")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.glob("calculator_grid_*.js")))


def test_calculator_navigation_sets_standalone_page_without_changing_workflow_stage() -> None:
    state = {"app_stage": "input", "itinerary_name": "Tromso"}

    open_calculator_page(state)

    assert state["active_app_page"] == CALCULATOR_PAGE
    assert state["app_stage"] == "input"
    assert calculator_page_is_active(state) is True
    assert state["calculator_state"].itinerary_name == "Tromso"
    assert len(state["calculator_state"].rows) == 25

    close_calculator_page(state)

    assert state["active_app_page"] == WORKFLOW_PAGE
    assert calculator_page_is_active(state) is False


def test_generated_itinerary_can_return_to_preserved_calculator_state() -> None:
    calculator_state = CalculatorState(
        itinerary_name="Return Trip",
        rows=(CalculatorRow(row_id="1", travel_element="Preserved hotel"),),
    )
    state = {
        "active_app_page": WORKFLOW_PAGE,
        "calculator_state": calculator_state,
        CALCULATOR_RETURN_AVAILABLE_KEY: True,
    }

    assert calculator_return_is_available(state) is True

    open_calculator_page(state)

    assert state["active_app_page"] == CALCULATOR_PAGE
    assert state["calculator_state"] == calculator_state

def test_calculator_navigation_rehydrates_empty_saved_snapshot_with_blank_rows() -> None:
    state = {"itinerary_name": "Saved Trip", "calculator_state": CalculatorState(itinerary_name="Saved Trip", rows=())}

    open_calculator_page(state)

    assert state["active_app_page"] == CALCULATOR_PAGE
    assert state["calculator_state"].itinerary_name == "Saved Trip"
    assert len(state["calculator_state"].rows) == 25


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


def test_calculator_table_shows_clean_blank_rows_without_formula_noise() -> None:
    table_data = rows_to_table_data((CalculatorRow(row_id="1"),), show_advanced=True)

    row = table_data[0]

    assert row["gross_price_per_unit"] is None
    assert row["units"] is None
    assert row["sales_price_per_unit"] == ""
    assert row["gross_price"] is None
    assert row["supplier_x_rate"] is None
    assert row["sales_x_rate"] is None


def test_calculator_table_recalculates_formula_fields_for_filled_rows() -> None:
    table_data = rows_to_table_data(
        (
            CalculatorRow(
                row_id="1",
                travel_element="Oslo hotel",
                gross_price_per_unit=200,
                units=1,
                supplier_currency="EUR",
                sales_currency="EUR",
            ),
        ),
        show_advanced=False,
    )

    row = table_data[0]

    assert row["gross_price"] == 200
    assert row["net_price"] == 200
    assert row["price"] == 200
    assert row["sales_price_nok_total"] == 2200
    assert row["gp_nok"] == 0


def test_calculator_table_treats_text_none_as_blank_sales_override() -> None:
    rows = table_data_to_rows(
        (
            {
                "row_id": "1",
                "travel_element": "Oslo hotel",
                "gross_price_per_unit": "200",
                "units": "1",
                "sales_price_per_unit": "None",
            },
        ),
        (),
    )

    assert rows[0].gross_price_per_unit == 200
    assert rows[0].units == 1
    assert rows[0].sales_price_per_unit is None


def test_calculator_table_displays_supplier_commission_as_percent() -> None:
    table_data = rows_to_table_data(
        (CalculatorRow(row_id="1", travel_element="Hotel", supplier_commission=0.15),),
        show_advanced=False,
    )

    assert table_data[0]["supplier_commission"] == 15


def test_calculator_table_converts_supplier_commission_percent_to_decimal() -> None:
    rows = table_data_to_rows(
        (
            {
                "row_id": "1",
                "travel_element": "Hotel",
                "gross_price_per_unit": "200",
                "units": "1",
                "supplier_commission": "15",
            },
        ),
        (),
    )

    assert rows[0].supplier_commission == 0.15


def test_calculator_table_detects_grid_user_edit_changes() -> None:
    from app_modules.calculator_grid_data import rows_have_user_edit_changes

    current = (CalculatorRow(row_id="1", travel_element="Hotel"),)
    edited = (CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit=200),)

    assert rows_have_user_edit_changes(edited, current) is True
    assert rows_have_user_edit_changes(current, current) is False


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

def _python_module_calls(relative_path: str) -> set[str]:
    import ast

    tree = ast.parse(Path(relative_path).read_text(encoding="utf-8"))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    return calls


def _python_imported_names(relative_path: str) -> set[str]:
    import ast

    tree = ast.parse(Path(relative_path).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
    return names


def _calculator_columns() -> list[dict[str, str | bool]]:
    import re

    source = Path("calculator_grid_component/frontend/js/calculator_grid_columns.js").read_text(encoding="utf-8")
    columns: list[dict[str, str | bool]] = []
    for raw_column in re.findall(r"\{([^{}]+)\}", source):
        column: dict[str, str | bool] = {}
        for key, quoted in re.findall(r"(\w+): '([^']*)'", raw_column):
            column[key] = quoted
        for key, boolean in re.findall(r"(\w+): (true|false)", raw_column):
            column[key] = boolean == "true"
        if "key" in column:
            columns.append(column)
    return columns


def _calculator_labels() -> set[str]:
    return {str(column.get("label")) for column in _calculator_columns()}


def test_calculator_keeps_main_workflow_contract_locked() -> None:
    from app_modules.workflow_config import FLOW_STAGES

    input_calls = _python_module_calls("app_modules/input_step.py")
    main_imports = _python_imported_names("app_modules/main_view.py")

    assert FLOW_STAGES == ("input", "edit", "pictures", "export")
    assert "open_calculator_page" in input_calls
    assert "open_local_library_page" in input_calls
    assert "calculator_page_is_active" in main_imports


def test_calculator_page_uses_browser_side_grid_not_streamlit_data_editor() -> None:
    imports = _python_imported_names("app_modules/calculator_page.py")
    calls = _python_module_calls("app_modules/calculator_page.py")

    assert "render_calculator_grid" in imports
    assert "render_currency_rate_editor" in imports
    assert "data_editor" not in calls


def test_calculator_component_column_model_uses_template_labels_and_percent_commission() -> None:
    columns = _calculator_columns()
    by_key = {column["key"]: column for column in columns}

    assert by_key["supplier_commission"]["label"] == "Supp Comm"
    assert by_key["supplier_commission"]["kind"] == "percent"
    assert by_key["sales_price_per_unit"]["label"] == "Sales P per unit"
    assert "Sales/unit calc" not in _calculator_labels()


def test_calculator_component_supports_keyboard_navigation_and_totals_panel() -> None:
    import re

    keyboard_source = _calculator_js_source("calculator_grid_keyboard.js")
    render_source = _calculator_js_source("calculator_grid_render.js")
    status_source = _calculator_js_source("calculator_grid_status_render.js")
    handled_keys = set(re.findall(r"event\.key === '([^']+)'", keyboard_source))
    dashboard_classes = set(re.findall(r"class=\"([^\"]+)\"", status_source))

    assert {"ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "Tab"} <= handled_keys
    assert "function handleCellKeydown(" in keyboard_source
    assert "function navigationMovement(" in keyboard_source
    assert 'id="calculator-dashboard-container"' in render_source
    assert "calculator-dashboard" in dashboard_classes
    assert "calculator-grid-hint" not in status_source
    assert "Total cost NOK" in status_source
    assert "Profit / GP NOK" in status_source
    assert "Cost per pax" in status_source
    assert "Sales per pax" in status_source


def test_old_streamlit_calculator_grid_config_module_is_removed() -> None:
    assert not Path("app_modules/calculator_grid_config.py").exists()


def test_calculator_page_exposes_local_library_refresh_controls() -> None:
    imports = _python_imported_names("app_modules/calculator_page.py")

    assert "render_local_library_refresh_control" in imports


def test_calculator_table_marks_automatic_sales_price_and_round_trips_it_as_none() -> None:
    source = CalculatorRow(
        row_id="1",
        gross_price_per_unit=1200,
        units=1,
        supplier_currency="NOK",
        sales_currency="EUR",
    )
    table = rows_to_table_data((source,), show_advanced=False, currency_rates={"NOK": 1, "EUR": 12})

    assert table[0]["sales_price_per_unit"] == 100
    assert table[0]["_sales_price_per_unit_touched"] is False

    restored = table_data_to_rows(table, (source,))
    assert restored[0].sales_price_per_unit is None
