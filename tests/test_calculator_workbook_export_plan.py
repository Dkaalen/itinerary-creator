from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from calculator.calculator_state import CalculatorState
from calculator.columns import CURRENCY_SHEET_NAME, KALK_SHEET_NAME
from calculator.row_model import CalculatorRow
from calculator.workbook_export import build_calculation_workbook, export_calculation_workbook
from calculator.workbook_import import import_calculation_workbook
from calculator.workbook_export_plan import (
    QUOTE_CELL,
    QUOTE_FORMULA,
    build_workbook_export_plan,
)
import calculator.workbook_package_export as package_export
from calculator.workbook_package_export import clear_workbook_package_export_cache


def _representative_state() -> CalculatorState:
    return CalculatorState(
        itinerary_name="Canonical plan",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Hotel",
                supplier="Nordic Hotel",
                travel_element="Two nights",
                manual_booking=True,
                comments="Long comment",
                non_refundable=True,
                gross_price_per_unit=125.5,
                units=2,
                supplier_commission=0.1,
                supplier_currency="eur",
                sales_price_per_unit=175,
                sales_currency="nok",
                vat25=25,
                net_price_override="=S7*0.75",
            ),
            CalculatorRow(
                row_id="2",
                type="Activity",
                travel_element="Formula row",
                gross_price_per_unit="=Q7/2",
                units=3,
                supplier_currency="NOK",
                sales_price_per_unit=0,
                sales_currency="EUR",
                gp_percent_override=0.33,
            ),
        ),
    )


def test_canonical_plan_owns_currency_rows_formulas_and_blank_rows() -> None:
    plan = build_workbook_export_plan(_representative_state(), {"NOK": 1, "EUR": 12})
    currency = plan.currency_cell_map()
    cells = plan.calculator_cell_map()

    assert currency["B2"].value == "NOK"
    assert currency["C3"].value == 12
    assert cells["K7"].kind == "boolean"
    assert cells["U7"].value == "=S7*0.75"
    assert cells["Y8"].value == "=IFERROR(Q8*W8/AB8,0)"
    assert cells["B9"].kind == "blank"
    assert cells["S9"].value == "=ROUND(Q9*R9,2)"
    assert cells[QUOTE_CELL].value == QUOTE_FORMULA
    assert cells["Y104"].kind == "blank"


def test_required_custom_currency_is_kept_inside_fixed_lookup_table() -> None:
    state = CalculatorState(
        rows=(
            CalculatorRow(
                row_id="1",
                gross_price_per_unit=100,
                units=1,
                supplier_currency="NZD",
                sales_currency="EUR",
            ),
        )
    )
    plan = build_workbook_export_plan(state, {"NZD": 6.25})
    currencies = {
        plan.currency_cells[index].value: plan.currency_cells[index + 1].value
        for index in range(0, len(plan.currency_cells), 2)
        if plan.currency_cells[index].value
    }

    assert currencies["NZD"] == 6.25
    assert len(currencies) == 12

    exported = export_calculation_workbook(state, currency_rates={"NZD": 6.25})
    imported = import_calculation_workbook(exported.content)
    assert imported.currency_rates["NZD"] == 6.25



def test_lookup_table_can_fit_twelve_required_non_default_currencies() -> None:
    codes = tuple(f"X{index:02d}" for index in range(12))
    rows = tuple(
        CalculatorRow(
            row_id=str(index),
            supplier_currency=code,
            sales_currency=code,
        )
        for index, code in enumerate(codes, start=1)
    )
    rates = {code: float(index) for index, code in enumerate(codes, start=1)}

    plan = build_workbook_export_plan(CalculatorState(rows=rows), rates)
    exported_codes = {
        plan.currency_cells[index].value
        for index in range(0, len(plan.currency_cells), 2)
    }

    assert exported_codes == set(codes)

def test_fast_and_openpyxl_renderers_apply_identical_planned_values() -> None:
    state = _representative_state()
    rates = {"NOK": 1, "EUR": 12, "USD": 9.5}
    plan = build_workbook_export_plan(state, rates)
    openpyxl_workbook = build_calculation_workbook(state, currency_rates=rates)
    fast_workbook = load_workbook(
        BytesIO(export_calculation_workbook(state, currency_rates=rates).content),
        data_only=False,
    )

    for cell in plan.currency_cells:
        openpyxl_value = openpyxl_workbook[CURRENCY_SHEET_NAME][cell.reference].value
        fast_value = fast_workbook[CURRENCY_SHEET_NAME][cell.reference].value
        if cell.kind == "blank":
            assert openpyxl_value in (None, "")
            assert fast_value in (None, "")
        else:
            assert openpyxl_value == fast_value == cell.value
    for cell in plan.calculator_cells:
        openpyxl_value = openpyxl_workbook[KALK_SHEET_NAME][cell.reference].value
        fast_value = fast_workbook[KALK_SHEET_NAME][cell.reference].value
        if cell.kind == "blank":
            assert openpyxl_value in (None, "")
            assert fast_value in (None, "")
        else:
            assert openpyxl_value == fast_value == cell.value

    assert openpyxl_workbook.calculation.calcMode == fast_workbook.calculation.calcMode == "auto"
    assert openpyxl_workbook.calculation.fullCalcOnLoad is True
    assert fast_workbook.calculation.fullCalcOnLoad is True
    assert openpyxl_workbook.calculation.forceFullCalc is True
    assert fast_workbook.calculation.forceFullCalc is True


def test_plan_fingerprint_changes_only_when_export_inputs_change() -> None:
    state = _representative_state()

    first = build_workbook_export_plan(state, {"NOK": 1, "EUR": 11})
    repeated = build_workbook_export_plan(state, {"NOK": 1, "EUR": 11})
    changed_rate = build_workbook_export_plan(state, {"NOK": 1, "EUR": 12})
    changed_row = build_workbook_export_plan(
        state.with_itinerary_name("Filename only"),
        {"NOK": 1, "EUR": 11},
    )

    assert first.fingerprint == repeated.fingerprint
    assert first.fingerprint != changed_rate.fingerprint
    assert first.fingerprint == changed_row.fingerprint


def test_fast_renderer_reuses_unchanged_package_bytes() -> None:
    clear_workbook_package_export_cache()
    state = _representative_state()

    first = export_calculation_workbook(state)
    repeated = export_calculation_workbook(state)
    changed = export_calculation_workbook(
        CalculatorState(rows=(*state.rows, CalculatorRow(row_id="3", travel_element="Changed")))
    )

    assert repeated.content is first.content
    assert changed.content != first.content


def test_fast_renderer_cache_keeps_only_two_workbooks() -> None:
    clear_workbook_package_export_cache()
    states = tuple(
        CalculatorState(
            rows=(CalculatorRow(row_id="1", travel_element=f"Version {index}"),)
        )
        for index in range(3)
    )

    first = export_calculation_workbook(states[0])
    export_calculation_workbook(states[1])
    export_calculation_workbook(states[2])

    assert len(package_export._EXPORT_CACHE) == 2
    rebuilt_first = export_calculation_workbook(states[0])
    assert rebuilt_first.content == first.content
    assert rebuilt_first.content is not first.content
