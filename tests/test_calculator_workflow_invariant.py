from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from app_modules.calculator_state_keys import CALCULATOR_STATE_KEY, CURRENCY_RATES_STATE_KEY
from app_modules.saved_project_calculator_state import (
    calculator_snapshot_from_workflow_state,
    calculator_state_from_snapshot,
)
from calculator.calculations import calculate_dashboard
from calculator.calculator_state import CalculatorState
from calculator.formula_map import TOTAL_FORMULAS, expected_row_formulas
from calculator.row_model import CalculatorRow
from calculator.state_serialization import calculator_state_from_json, calculator_state_to_json
from calculator.workbook_export import export_calculation_workbook


def test_calculate_save_reload_and_export_invariant() -> None:
    rates = {"NOK": 1, "EUR": 12.345678, "USD": 9.876543}
    state = CalculatorState(
        itinerary_name="Nordic Group",
        number_of_pax=17,
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Hotel",
                travel_element="Oslo hotel",
                gross_price_per_unit=125.55,
                units=17,
                supplier_commission=0.12,
                supplier_currency="EUR",
                sales_price_per_unit=189.95,
                sales_currency="EUR",
                vat25=250.25,
            ),
            CalculatorRow(
                row_id="2",
                day="Day 2",
                type="Activity",
                travel_element="Fjord cruise",
                gross_price_per_unit=75.005,
                units=17,
                supplier_currency="USD",
                sales_price_per_unit=105.50,
                sales_currency="EUR",
                sales_x_rate_override=12.5,
                vat0_international=100,
            ),
        ),
    )

    before = calculate_dashboard(state.rows, state.number_of_pax, rates)
    json_restored = calculator_state_from_json(calculator_state_to_json(state))
    after_json = calculate_dashboard(json_restored.rows, json_restored.number_of_pax, rates)

    snapshot = calculator_snapshot_from_workflow_state(
        {CALCULATOR_STATE_KEY: state, CURRENCY_RATES_STATE_KEY: rates}
    )
    project_restored = calculator_state_from_snapshot(snapshot)
    after_project = calculate_dashboard(project_restored.rows, project_restored.number_of_pax, snapshot["currency_rates"])

    assert json_restored == state
    assert project_restored == state
    assert after_json == before
    assert after_project == before

    export = export_calculation_workbook(project_restored, currency_rates=snapshot["currency_rates"])
    workbook = load_workbook(BytesIO(export.content), data_only=False)
    sheet = workbook["Kalk"]

    assert sheet["J7"].value == "Oslo hotel"
    assert sheet["J8"].value == "Fjord cruise"
    assert sheet["W7"].value == expected_row_formulas(7)["W"]
    assert sheet["AB7"].value == expected_row_formulas(7)["AB"]
    assert sheet["AB8"].value == 12.5
    assert sheet["AF101"].value == TOTAL_FORMULAS["AF101"]
    assert sheet["AJ101"].value == TOTAL_FORMULAS["AJ101"]
    assert sheet["Y104"].value is None
    assert sheet["Z104"].value is None
    assert workbook.calculation.fullCalcOnLoad is True
    assert workbook.calculation.forceFullCalc is True
