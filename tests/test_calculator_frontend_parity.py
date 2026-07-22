from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from calculator.calculations import calculate_row, calculate_totals
from calculator.row_model import CalculatorRow

_FRONTEND = Path(__file__).resolve().parents[1] / "calculator_grid_component" / "frontend" / "js"


def test_frontend_and_python_formula_engines_match_reference_vectors() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )
    vectors = [
        {
            "gross_price_per_unit": 100,
            "units": 3,
            "supplier_commission": 20,
            "supplier_currency": "NOK",
            "sales_price_per_unit": 150,
            "sales_currency": "EUR",
        },
        {
            "gross_price_per_unit": 1.005,
            "units": 1,
            "supplier_commission": 0,
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
        },
        {
            "gross_price_per_unit": -1.005,
            "units": 2,
            "supplier_commission": 12.5,
            "supplier_currency": "USD",
            "sales_price_per_unit": -2.25,
            "sales_currency": "EUR",
        },
        {
            "gross_price_per_unit": 100,
            "units": 0,
            "supplier_commission": 0,
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
        },
        {
            "gross_price_per_unit": 404.775,
            "units": 12.2,
            "supplier_commission": 26.15,
            "supplier_currency": "EUR",
            "sales_price_per_unit": 258.026,
            "sales_currency": "USD",
        },
        {
            "gross_price_per_unit": -332.775,
            "units": 19.4,
            "supplier_commission": 22.09,
            "supplier_currency": "NOK",
            "sales_price_per_unit": -220.474,
            "sales_currency": "EUR",
        },
    ]
    script = (
        source
        + "\nconst vectors = "
        + json.dumps(vectors)
        + ";\n"
        + "const results = vectors.map((values, index) => {"
        + " const row = {...createBlankRow(String(index + 1)), ...values};"
        + " if (values.sales_price_per_unit !== undefined) row._sales_price_per_unit_touched = true;"
        + " return calculateRow(row, DEFAULT_RATES);"
        + "});"
        + "console.log(JSON.stringify(results));\n"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    frontend_rows = json.loads(completed.stdout)

    for values, frontend in zip(vectors, frontend_rows):
        python_row = CalculatorRow(
            gross_price_per_unit=values["gross_price_per_unit"],
            units=values["units"],
            supplier_commission=values["supplier_commission"] / 100,
            supplier_currency=values["supplier_currency"],
            sales_price_per_unit=values.get("sales_price_per_unit"),
            sales_currency=values["sales_currency"],
        )
        backend = calculate_row(python_row)
        for field in (
            "gross_price",
            "net_price",
            "supplier_x_rate",
            "net_price_nok",
            "price",
            "sales_x_rate",
            "sales_price_nok_total",
            "gp_nok",
            "gp_percent",
        ):
            assert frontend[field] == pytest.approx(getattr(backend, field), abs=1e-9), field


def test_frontend_and_python_total_rounding_match_excel_sum_semantics() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )
    script = source + """
const rows = [createBlankRow('1'), createBlankRow('2')];
rows[0].vat25 = 0.005;
rows[1].vat25 = 0.005;
rows.forEach((row) => calculateRow(row, DEFAULT_RATES));
console.log(JSON.stringify(calculateTotals(rows)));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    frontend_totals = json.loads(completed.stdout)
    backend_totals = calculate_totals(
        [
            CalculatorRow(row_id="1", vat25=0.005),
            CalculatorRow(row_id="2", vat25=0.005),
        ]
    )

    assert frontend_totals["vat25"] == backend_totals.vat25 == 0.01


def test_frontend_contains_excel_style_state_safety_features() -> None:
    actions = (_FRONTEND / "calculator_grid_actions.js").read_text(encoding="utf-8")
    controller = (_FRONTEND / "calculator_grid_state_controller.js").read_text(encoding="utf-8")
    selection = (_FRONTEND / "calculator_grid_selection.js").read_text(encoding="utf-8")
    history = (_FRONTEND / "calculator_grid_history.js").read_text(encoding="utf-8")
    toolbar_render = (_FRONTEND / "calculator_grid_toolbar_render.js").read_text(encoding="utf-8")
    status_render = (_FRONTEND / "calculator_grid_status_render.js").read_text(encoding="utf-8")

    assert "scheduleLocalDraftSave" in controller
    assert "scheduleRecoverySnapshot" in controller
    assert "submitAction('sync')" not in controller
    assert "applyTsvAtActiveCell" in selection
    assert "fillSelection" in selection
    assert "undoCalculatorChange" in history
    assert "redoCalculatorChange" in history
    assert 'data-action="formula-bar"' in toolbar_render
    assert 'data-action="set-pax"' in status_render


def test_frontend_validation_surfaces_invalid_cells_and_rates() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
            "calculator_grid_validation.js",
        )
    )
    script = source + """
const row = createBlankRow('1');
row.gross_price_per_unit = '=10/0';
row.supplier_currency = 'XYZ';
row.sales_currency = 'NOK';
const state = {rows: [row], numberOfPax: '2.5', currencyRates: DEFAULT_RATES};
console.log(JSON.stringify(validateCalculatorState(state)));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    errors = json.loads(completed.stdout)

    assert {error["code"] for error in errors} == {"invalid_number", "invalid_pax", "missing_rate"}


def test_frontend_validation_scopes_match_calculator_actions() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
            "calculator_grid_validation.js",
        )
    )
    script = source + """
const row = createBlankRow('9');
row.day = 'Day 1';
row.type = 'Hotel';
row.travel_element = 'Oslo hotel';
row.gross_price_per_unit = '=10/0';
row.supplier_currency = 'XYZ';
row.sales_currency = 'NOK';
const state = {rows: [row], numberOfPax: '2.5', currencyRates: DEFAULT_RATES};
console.log(JSON.stringify({
  draft: calculatorValidationErrors(state, CALCULATOR_VALIDATION_SCOPE.DRAFT_SAFE),
  persistence: calculatorValidationErrors(state, CALCULATOR_VALIDATION_SCOPE.PERSISTENCE),
  export: calculatorValidationErrors(state, CALCULATOR_VALIDATION_SCOPE.EXPORT),
  generation: calculatorValidationErrors(state, CALCULATOR_VALIDATION_SCOPE.GENERATION)
}));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    scopes = json.loads(completed.stdout)

    assert scopes["draft"] == []
    assert {error["code"] for error in scopes["persistence"]} == {"invalid_number", "invalid_pax"}
    assert {error["code"] for error in scopes["export"]} == {"invalid_number", "missing_rate"}
    assert scopes["generation"] == []


def test_frontend_and_python_expression_inputs_match() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )
    expressions = ["=404.775*12.2", "=32.425*18.2", "=1.005", "=2.675", "100*(1-20%)"]
    script = (
        source
        + "\nconst expressions = "
        + json.dumps(expressions)
        + ";\n"
        + "console.log(JSON.stringify(expressions.map((value, index) => {"
        + " const row = {...createBlankRow(String(index + 1)), gross_price_per_unit: value, units: 1, supplier_currency: 'NOK', sales_currency: 'NOK'};"
        + " return calculateRow(row, DEFAULT_RATES).gross_price;"
        + "})));\n"
    )
    completed = subprocess.run(
        ["node"],
        input=script,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    frontend_values = json.loads(completed.stdout)
    backend_values = [
        calculate_row(
            CalculatorRow(
                gross_price_per_unit=expression,
                units=1,
                supplier_currency="NOK",
                sales_currency="NOK",
            )
        ).gross_price
        for expression in expressions
    ]

    assert frontend_values == backend_values


def test_frontend_distinguishes_grid_navigation_from_cell_text_editing() -> None:
    caret = (_FRONTEND / "calculator_grid_caret.js").read_text(encoding="utf-8")
    keyboard = (_FRONTEND / "calculator_grid_keyboard.js").read_text(encoding="utf-8")
    editing = (_FRONTEND / "calculator_grid_cell_editing.js").read_text(encoding="utf-8")
    suggestions = (_FRONTEND / "calculator_grid_suggestions.js").read_text(encoding="utf-8")

    assert "let activeCellEditing = false" in caret
    assert "if (activeCellEditing)" in keyboard
    assert "event.key === 'F2' || event.key === 'Enter'" in keyboard
    assert "isPrintableCellKey" in keyboard
    assert "placeCaretAtEnd" in caret
    assert "setCellEditingMode" in editing
    assert "activeCellEditing = false" in suggestions
    assert "setSingleCellSelection(active.rowIndex, 'travel_element')" in suggestions


def test_navigation_movement_leaves_enter_for_edit_mode() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = (_FRONTEND / "calculator_grid_keyboard.js").read_text(encoding="utf-8")
    script = source + """
console.log(JSON.stringify({
  left: navigationMovement({key: 'ArrowLeft', shiftKey: false}),
  tab: navigationMovement({key: 'Tab', shiftKey: true}),
  enter: navigationMovement({key: 'Enter', shiftKey: false}),
  printable: isPrintableCellKey({key: 'a', ctrlKey: false, metaKey: false, altKey: false}),
  modified: isPrintableCellKey({key: 'a', ctrlKey: true, metaKey: false, altKey: false})
}));
"""
    completed = subprocess.run(
        ["node"],
        input=script,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    result = json.loads(completed.stdout)

    assert result == {
        "left": {"rowDelta": 0, "colDelta": -1},
        "tab": {"rowDelta": 0, "colDelta": -1},
        "enter": None,
        "printable": True,
        "modified": False,
    }


def test_frontend_exposes_advanced_excel_interactions() -> None:
    advanced = (_FRONTEND / "calculator_grid_advanced_actions.js").read_text(encoding="utf-8")
    toolbar_render = (_FRONTEND / "calculator_grid_toolbar_render.js").read_text(encoding="utf-8")
    grid_render = (_FRONTEND / "calculator_grid_grid_render.js").read_text(encoding="utf-8")
    actions = (_FRONTEND / "calculator_grid_actions.js").read_text(encoding="utf-8")
    submission_actions = (_FRONTEND / "calculator_grid_submission_actions.js").read_text(encoding="utf-8")
    draft = (_FRONTEND / "calculator_grid_draft_storage.js").read_text(encoding="utf-8")

    for contract in (
        "insertRowsAtSelection",
        "duplicateSelectedRows",
        "deleteSelectedRows",
        "startFillDrag",
        "beginColumnResize",
        "findNextCalculatorMatch",
        "replaceAllCalculatorMatches",
    ):
        assert contract in advanced
    assert 'data-action="insert-above"' in toolbar_render
    assert 'data-action="find-replace"' in toolbar_render
    assert 'class="column-resize-handle"' in grid_render
    assert "bindAdvancedCalculatorEvents" in actions
    assert "beforeunload" in submission_actions
    assert "columnWidths" in draft


def test_frontend_dashboard_reports_currency_exposure_without_changing_totals() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )
    script = source + """
const rows = [
  {...createBlankRow('1'), gross_price_per_unit: 100, units: 2, supplier_currency: 'EUR', sales_price_per_unit: 150, sales_currency: 'NOK'},
  {...createBlankRow('2'), gross_price_per_unit: 50, units: 1, supplier_currency: 'USD', sales_price_per_unit: 80, sales_currency: 'EUR'}
];
calculateRows(rows, {NOK: 1, EUR: 12, USD: 10});
console.log(JSON.stringify(calculateDashboard({rows, numberOfPax: 5})));
"""
    completed = subprocess.run(
        ["node"], input=script, check=True, capture_output=True, text=True, timeout=15
    )
    dashboard = json.loads(completed.stdout)

    assert dashboard["number_of_pax"] == 5
    assert dashboard["cost_per_pax"] == pytest.approx(dashboard["net_price_nok"] / 5, abs=0.01)
    assert dashboard["currency_exposure"]["supplier"] == [["EUR", 200], ["USD", 50]]
    assert dashboard["currency_exposure"]["sales"] == [["EUR", 80], ["NOK", 300]]


def test_frontend_a1_references_match_python_dependency_engine() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )
    script = source + """
const rows = [createBlankRow('1'), createBlankRow('2')];
rows[0].gross_price_per_unit = 100;
rows[0].units = 2;
rows[0].supplier_currency = 'NOK';
rows[0].sales_currency = 'NOK';
rows[1].gross_price_per_unit = '=S7/4';
rows[1].units = 3;
rows[1].supplier_currency = 'NOK';
rows[1].sales_currency = 'NOK';
rows[1].price_override = '=$Q$7*R8';
calculateRows(rows, DEFAULT_RATES);
console.log(JSON.stringify(rows));
"""
    completed = subprocess.run(["node"], input=script, check=True, capture_output=True, text=True, timeout=15)
    frontend = json.loads(completed.stdout)

    backend_rows = (
        CalculatorRow(row_id="1", gross_price_per_unit=100, units=2, supplier_currency="NOK", sales_currency="NOK"),
        CalculatorRow(row_id="2", gross_price_per_unit="=S7/4", units=3, supplier_currency="NOK", sales_currency="NOK", price_override="=$Q$7*R8"),
    )
    from calculator.calculations import calculate_rows

    backend = calculate_rows(backend_rows)
    assert frontend[1]["gross_price"] == backend[1].gross_price
    assert frontend[1]["price"] == backend[1].price
    assert frontend[1]["sales_price_nok_total"] == backend[1].sales_price_nok_total


def test_frontend_formula_translation_respects_relative_and_absolute_references() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")
    source = (_FRONTEND / "calculator_grid_formula_input.js").read_text(encoding="utf-8")
    script = source + """
console.log(JSON.stringify({
  down: translateFormulaReferences('=Q7*$R$7+$S7+T$7', 2, 0),
  right: translateFormulaReferences('=Q7*$R$7+$S7+T$7', 0, 2),
  invalid: translateFormulaReferences('=A1', -2, 0)
}));
"""
    completed = subprocess.run(["node"], input=script, check=True, capture_output=True, text=True, timeout=15)
    result = json.loads(completed.stdout)
    assert result == {
        "down": "=Q9*$R$7+$S9+T$7",
        "right": "=S7*$R$7+$S7+V$7",
        "invalid": "=#REF!",
    }


def test_frontend_formula_engine_handles_full_93_row_dependency_chain_quickly() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")
    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )
    script = source + """
const rows = Array.from({length: 93}, (_, index) => {
  const row = createBlankRow(String(index + 1));
  row.gross_price_per_unit = index === 0 ? 100 : `=S${6 + index}/2`;
  row.units = 2;
  row.supplier_currency = 'NOK';
  row.sales_currency = 'NOK';
  return row;
});
const started = Date.now();
for (let pass = 0; pass < 50; pass += 1) calculateRows(rows, DEFAULT_RATES);
console.log(JSON.stringify({elapsed: Date.now() - started, final: rows[92].gross_price}));
"""
    completed = subprocess.run(["node"], input=script, check=True, capture_output=True, text=True, timeout=15)
    result = json.loads(completed.stdout)
    assert result["elapsed"] < 5000
    assert result["final"] == 200
