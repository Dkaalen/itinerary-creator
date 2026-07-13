from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import load_workbook

from calculator.calculations import calculate_rows, calculate_totals
from calculator.calculator_state import CalculatorState
from calculator.cell_formula_engine import CalculatorCellFormulaEvaluator, CellFormulaError, formula_references
from calculator.row_model import CalculatorRow
from calculator.validation import validate_calculator_state
from calculator.workbook_export import export_calculation_workbook


def test_cross_row_a1_references_recalculate_dependencies() -> None:
    rows = (
        CalculatorRow(row_id="1", gross_price_per_unit="=Q8*2", units=2, supplier_currency="NOK", sales_currency="NOK"),
        CalculatorRow(row_id="2", gross_price_per_unit=50, units=3, supplier_currency="NOK", sales_currency="NOK"),
    )

    calculated = calculate_rows(rows)

    assert calculated[0].gross_price == 200
    assert calculated[0].price == 200
    assert calculated[1].gross_price == 150
    assert calculate_totals(rows).price == 350


def test_absolute_references_and_formula_overrides_are_supported() -> None:
    rows = (
        CalculatorRow(
            row_id="1",
            gross_price_per_unit=100,
            units=2,
            price_override="=$Q$7*3",
            supplier_currency="NOK",
            sales_currency="NOK",
        ),
    )

    calculated = calculate_rows(rows)[0]

    assert calculated.price == 300
    assert calculated.sales_price_nok_total == 300


def test_circular_reference_is_detected_and_reported() -> None:
    rows = (
        CalculatorRow(row_id="1", gross_price_per_unit="=Q8", units=1),
        CalculatorRow(row_id="2", gross_price_per_unit="=Q7", units=1),
    )

    with pytest.raises(CellFormulaError, match="Circular reference") as error:
        CalculatorCellFormulaEvaluator(rows).evaluate_cell("Q7")

    assert error.value.code == "#CIRC!"
    issues = validate_calculator_state(CalculatorState(rows=rows))
    assert any(issue.code == "#CIRC!" for issue in issues)


def test_text_cell_reference_is_rejected() -> None:
    row = CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit="=J7*2", units=1)

    with pytest.raises(CellFormulaError) as error:
        CalculatorCellFormulaEvaluator((row,)).evaluate_cell("Q7")

    assert error.value.code == "#VALUE!"


def test_formula_reference_discovery_normalizes_absolute_markers() -> None:
    assert formula_references("=$Q$7 + R8 + Q7") == ("Q7", "R8", "Q7")


def test_export_keeps_user_a1_formula_and_canonical_dependents() -> None:
    state = CalculatorState(
        rows=(
            CalculatorRow(row_id="1", gross_price_per_unit="=Q8*2", units=1, supplier_currency="NOK", sales_currency="NOK"),
            CalculatorRow(row_id="2", gross_price_per_unit=50, units=1, supplier_currency="NOK", sales_currency="NOK"),
        )
    )

    workbook = load_workbook(BytesIO(export_calculation_workbook(state).content), data_only=False)
    sheet = workbook["Kalk"]

    assert sheet["Q7"].value == "=Q8*2"
    assert sheet["S7"].value == "=ROUND(Q7*R7,2)"
    assert sheet["AC7"].value == "=ROUND(Z7*AB7,2)"
