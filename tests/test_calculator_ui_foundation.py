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


def test_calculator_keeps_main_workflow_contract_locked() -> None:
    config_source = Path("app_modules/workflow_config.py").read_text(encoding="utf-8")
    input_source = Path("app_modules/input_step.py").read_text(encoding="utf-8")
    main_view_source = Path("app_modules/main_view.py").read_text(encoding="utf-8")

    assert 'FLOW_STAGES = ("input", "edit", "pictures", "export")' in config_source
    assert "render_calculator_entry_button" in input_source
    assert "calculator_page_is_active" in main_view_source


def test_calculator_page_uses_browser_side_grid_not_streamlit_data_editor() -> None:
    source = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")

    assert "st.data_editor" not in source
    assert "Recalculate / save edits" not in source
    assert "render_calculator_grid" in source
    assert "render_currency_rate_editor" in source


def test_calculator_component_column_model_uses_template_labels_and_percent_commission() -> None:
    source = Path("calculator_grid_component/frontend/js/calculator_grid_columns.js").read_text(encoding="utf-8")

    assert "app_modules/calculator_grid_config.py" not in source
    assert "supplier_commission" in source
    assert "Supp Comm" in source
    assert "Sales P per unit" in source
    assert "Sales/unit calc" not in source
    assert "kind: 'percent'" in source


def test_calculator_component_supports_keyboard_navigation_and_totals_panel() -> None:
    app_source = _calculator_js_source("calculator_grid_cell_editing.js")
    render_source = Path("calculator_grid_component/frontend/js/calculator_grid_render.js").read_text(encoding="utf-8")

    assert "ArrowRight" in app_source
    assert "calculator-grid-hint" not in render_source
    assert "calculator-totals-panel" in render_source
    assert "Total net NOK" in render_source
    assert "Earnings / GP NOK" in render_source


def test_old_streamlit_calculator_grid_config_module_is_removed() -> None:
    assert not Path("app_modules/calculator_grid_config.py").exists()


def test_calculator_page_exposes_local_library_refresh_controls() -> None:
    source = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")

    assert "render_local_library_refresh_control" in source
    assert "force_refresh=refresh_library" in source
    assert "render_local_library_status" in source


def test_local_library_controls_keep_refresh_separate_from_cache_logic() -> None:
    source = Path("app_modules/calculator_library_controls.py").read_text(encoding="utf-8")

    assert "Refresh library" in source
    assert "read_cached_local_library" not in source
    assert "summarize_local_library_read" in source


def test_calculator_table_accepts_spreadsheet_style_numeric_expressions() -> None:
    rows = table_data_to_rows(
        (
            {
                "row_id": "1",
                "travel_element": "Activity",
                "gross_price_per_unit": "100/10*0.8",
                "units": "=2+1",
                "supplier_commission": "20%",
                "price": "=30*2",
            },
        ),
        (),
    )

    assert rows[0].gross_price_per_unit == 8
    assert rows[0].units == 3
    assert rows[0].supplier_commission == 0.2
    assert rows[0].price_override == 60


def test_calculator_component_uses_debounced_non_intrusive_suggestions_and_formula_parser() -> None:
    app_source = _calculator_js_source("calculator_grid_suggestions.js", "calculator_grid_actions.js")
    css_source = Path("calculator_grid_component/frontend/styles/calculator_grid.css").read_text(encoding="utf-8")
    index_source = Path("calculator_grid_component/frontend/index.html").read_text(encoding="utf-8")
    parser_source = Path("calculator_grid_component/frontend/js/calculator_grid_formula_input.js").read_text(encoding="utf-8")

    assert "SUGGESTION_MIN_QUERY_LENGTH = 3" in app_source
    assert "SUGGESTION_DEBOUNCE_MS" in app_source
    assert "renderSuggestionPanelOnly" in app_source
    assert "requestAnimationFrame(setCalculatorFrameHeight);" not in app_source.split("function renderSuggestionPanelOnly", 1)[1].split("function submitAction", 1)[0]
    assert ".suggestion-panel" in css_source
    assert "position: fixed;" in css_source
    assert "calculator_grid_formula_input.js" in index_source
    assert "class NumericExpressionParser" in parser_source
    assert "eval(" not in parser_source
    assert "new Function" not in parser_source


def test_calculator_browser_grid_hides_excel_advanced_columns_by_default() -> None:
    columns_source = Path("calculator_grid_component/frontend/js/calculator_grid_columns.js").read_text(encoding="utf-8")

    assert "advanced: true" in columns_source
    assert "return CALCULATOR_COLUMNS.filter((column) => showAdvanced || !column.advanced);" in columns_source
    for key in (
        "from_time",
        "to_time",
        "supplier",
        "manual_booking",
        "status",
        "comments",
        "non_refundable",
        "refundable",
        "url",
        "vat25",
        "vat15",
        "vat12",
        "vat0_domestic",
        "vat0_international",
    ):
        assert f"key: '{key}'" in columns_source


def test_calculator_browser_grid_has_fullscreen_control_and_fixed_width_cells() -> None:
    render_source = Path("calculator_grid_component/frontend/js/calculator_grid_render.js").read_text(encoding="utf-8")
    app_source = Path("calculator_grid_component/frontend/js/calculator_grid_fullscreen.js").read_text(encoding="utf-8")
    css_source = Path("calculator_grid_component/frontend/styles/calculator_grid.css").read_text(encoding="utf-8")

    assert "Fullscreen calculator" in render_source
    assert "data-action=\"toggle-fullscreen\"" in render_source
    assert "function toggleCalculatorFullscreen" in app_source
    assert "requestFullscreen" in app_source
    assert "calculator-grid-shell.fullscreen" in css_source
    assert "tableWidth(columns)" in render_source
    assert "dynamicColumnWidth" in render_source
    assert "max-width:${width}px" in render_source
    assert "setCalculatorHostFullscreen" in Path("calculator_grid_component/frontend/js/streamlit_bridge.js").read_text(encoding="utf-8")
    assert "text-overflow: ellipsis" not in css_source
    assert "text-overflow: clip" in css_source


def test_calculator_browser_grid_defaults_sales_and_commission_without_user_override() -> None:
    math_source = Path("calculator_grid_component/frontend/js/calculator_grid_math.js").read_text(encoding="utf-8")
    library_source = Path("calculator_grid_component/frontend/js/calculator_grid_library.js").read_text(encoding="utf-8")

    assert "DEFAULT_SUPPLIER_COMMISSION_PERCENT" not in math_source
    assert "applyDefaultSupplierCommission" not in math_source
    assert "refreshDefaultedEditableCells(rowIndex);" in _calculator_js_source("calculator_grid_cell_editing.js")
    assert "row.sales_price_per_unit = grossPerUnit" in math_source
    assert "_sales_price_per_unit_touched" in math_source
    assert "fetched.supplier_commission = DEFAULT_SUPPLIER_COMMISSION_PERCENT" not in library_source
    assert "fetched.sales_price_per_unit = '';" in library_source
    assert "applyDefaultUnits(row, grossPerUnit);" in math_source
    assert "percentPointInputValue" in _calculator_js_source("calculator_grid_cell_editing.js")



def test_calculator_grid_autofills_dates_from_day_one_arrival() -> None:
    date_source = Path("calculator_grid_component/frontend/js/calculator_grid_dates.js").read_text(encoding="utf-8")
    app_source = _calculator_js_source("calculator_grid_cell_editing.js")
    index_source = Path("calculator_grid_component/frontend/index.html").read_text(encoding="utf-8")

    assert "function autofillDatesFromArrival" in date_source
    assert "parseDayNumber" in date_source
    assert "formatGridDate(addDays(context.date, dayNumber - 1), context.format)" in date_source
    assert "markDayChanged(row)" in app_source
    assert "markDateManualState(row, key, rawValue)" in app_source
    assert "_from_date_auto" in date_source
    assert "refreshDateCells" in app_source
    assert "calculator_grid_dates.js" in index_source


def test_calculator_grid_uses_dynamic_widths_and_full_page_css() -> None:
    columns_source = Path("calculator_grid_component/frontend/js/calculator_grid_columns.js").read_text(encoding="utf-8")
    page_source = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")

    assert "minWidth" in columns_source
    assert "maxWidth" in columns_source
    assert "fitChars" in columns_source
    assert "section.main > div.block-container" in page_source
    assert "max-width: min(100% - 1.6rem, 1920px)" in page_source


def test_calculator_currency_defaults_and_full_width_layout_are_locked() -> None:
    math_source = Path("calculator_grid_component/frontend/js/calculator_grid_math.js").read_text(encoding="utf-8")
    page_source = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")

    assert "EUR: 11" in math_source
    assert "NOK: 1" in math_source
    assert "USD: 10" in math_source
    assert "GBP: 13" in math_source
    assert "width: min(100% - 1.6rem, 1920px)" in page_source
    assert 'iframe[title="calculator_grid"]' in page_source


def test_calculator_exposes_visible_currency_rate_editor() -> None:
    page_source = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")
    controls_source = Path("app_modules/calculator_currency_controls.py").read_text(encoding="utf-8")

    assert "render_currency_rate_editor" in page_source
    assert "Currency rates" in controls_source
    assert "Base currency is NOK" in controls_source
    assert "Reset currency rates" in controls_source


def test_calculator_component_removed_permanent_instruction_banner() -> None:
    render_source = Path("calculator_grid_component/frontend/js/calculator_grid_render.js").read_text(encoding="utf-8")

    assert "Edit directly in the sheet" not in render_source
    assert "calculator-grid-hint" not in render_source


def test_calculator_grid_app_shell_delegates_to_focused_modules() -> None:
    frontend = Path("calculator_grid_component/frontend")
    index_source = (frontend / "index.html").read_text(encoding="utf-8")
    app_lines = (frontend / "js/calculator_grid_app.js").read_text(encoding="utf-8").splitlines()

    for asset in (
        "calculator_grid_state_controller.js",
        "calculator_grid_cell_editing.js",
        "calculator_grid_suggestions.js",
        "calculator_grid_fullscreen.js",
        "calculator_grid_actions.js",
    ):
        assert f"js/{asset}" in index_source
        assert (frontend / "js" / asset).exists()
    assert len(app_lines) < 80
    assert "function bindEvents" not in "\n".join(app_lines)
    assert "function handleCellInput" not in "\n".join(app_lines)
