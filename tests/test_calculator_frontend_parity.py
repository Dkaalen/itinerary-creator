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
    render = (_FRONTEND / "calculator_grid_render.js").read_text(encoding="utf-8")

    assert "scheduleBackendSync" in controller and "submitAction('sync')" in controller
    assert "applyTsvAtActiveCell" in selection
    assert "fillSelection" in selection
    assert "undoCalculatorChange" in history
    assert "redoCalculatorChange" in history
    assert 'data-action="formula-bar"' in render
    assert 'data-action="set-pax"' in render


def test_frontend_validation_surfaces_invalid_cells_and_rates() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
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


def test_frontend_and_python_expression_inputs_match() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    source = "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
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
