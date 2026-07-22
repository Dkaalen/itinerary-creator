from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess

from openpyxl import load_workbook
import pytest

from app_modules.calculator_grid_data import rows_to_table_data
from calculator.calculations import (
    calculate_rows,
    calculate_totals,
    sales_price_per_unit_for_margin,
)
from calculator.calculator_state import CalculatorState
from calculator.financial_rules import (
    FINANCIAL_RULES_VERSION,
    financial_rules_payload,
)
from calculator.formula_map import TOTAL_FORMULAS
from calculator.row_model import CalculatorRow
from calculator.state_serialization import calculator_state_from_dict, calculator_state_to_dict
from calculator.workbook_export import export_calculation_workbook
from calculator.workbook_import import import_calculation_workbook

_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND = _ROOT / "calculator_grid_component" / "frontend" / "js"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "calculator_financial_parity_cases.json"
_CALCULATED_FIELDS = (
    "gross_price",
    "net_price",
    "supplier_x_rate",
    "net_price_nok",
    "price",
    "sales_x_rate",
    "sales_price_nok_total",
    "gp_nok",
    "gp_percent",
)
_TOTAL_FIELDS = (
    "price",
    "sales_price_nok_total",
    "gp_nok",
    "gp_percent",
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
)


def _cases() -> list[dict]:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    return payload["cases"]


def _rows(case: dict) -> tuple[CalculatorRow, ...]:
    return tuple(CalculatorRow(**row) for row in case["rows"])


def _frontend_source() -> str:
    return "\n".join(
        (_FRONTEND / filename).read_text(encoding="utf-8")
        for filename in (
            "calculator_grid_columns.js",
            "calculator_grid_formula_input.js",
            "calculator_grid_math.js",
            "calculator_grid_currency.js",
            "calculator_grid_state.js",
        )
    )


def test_financial_rules_contract_is_versioned_and_explicit() -> None:
    payload = financial_rules_payload()

    assert payload["version"] == FINANCIAL_RULES_VERSION
    assert payload["precision_digits"] == {"money": 2, "rate": 6, "percent": 6}
    assert payload["commission_ui_scale"] == 100
    assert payload["margin_basis"] == "net_price_nok"
    assert payload["sales_price_derived_override_fields"] == [
        "price_override",
        "sales_price_nok_total_override",
        "gp_nok_override",
        "gp_percent_override",
    ]


def test_browser_fallback_contract_matches_python_owned_rules() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    script = _frontend_source() + "\nconsole.log(JSON.stringify(DEFAULT_FINANCIAL_RULES));\n"
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert json.loads(completed.stdout) == financial_rules_payload()


def test_browser_and_python_match_all_financial_parity_fixtures() -> None:
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable.")

    cases = _cases()
    browser_cases = []
    for case in cases:
        rows = _rows(case)
        browser_cases.append(
            {
                "name": case["name"],
                "rates": case["rates"],
                "rows": rows_to_table_data(rows, show_advanced=True, currency_rates=case["rates"]),
            }
        )
    script = _frontend_source() + """
const cases = JSON.parse(process.argv[1]);
const rules = JSON.parse(process.argv[2]);
setActiveFinancialRules(rules);
const output = cases.map((item) => {
  const rows = calculateRows(item.rows.map((row) => ({...row})), item.rates);
  const evaluator = new CalculatorGridFormulaEvaluator(rows, item.rates);
  const calculatedSales = rows.map((_row, index) => evaluator.evaluateCell(`Y${CALCULATOR_DATA_START_ROW + index}`));
  return {name: item.name, rows, totals: calculateTotals(rows), calculatedSales};
});
console.log(JSON.stringify(output));
"""
    completed = subprocess.run(
        ["node", "-e", script, json.dumps(browser_cases), json.dumps(financial_rules_payload())],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    frontend = {item["name"]: item for item in json.loads(completed.stdout)}

    for case in cases:
        rows = _rows(case)
        backend_rows = calculate_rows(rows, case["rates"])
        backend_totals = calculate_totals(rows, case["rates"])
        browser = frontend[case["name"]]
        for index, (backend, browser_row) in enumerate(zip(backend_rows, browser["rows"])):
            for field in _CALCULATED_FIELDS:
                assert browser_row[field] == pytest.approx(getattr(backend, field), abs=1e-8), (
                    case["name"],
                    field,
                )
            assert browser["calculatedSales"][index] == pytest.approx(
                backend.calculated_sales_price_per_unit,
                abs=1e-8,
            )
        for field in _TOTAL_FIELDS:
            assert browser["totals"][field] == pytest.approx(getattr(backend_totals, field), abs=1e-8), (
                case["name"],
                field,
            )


def test_project_save_reload_preserves_financial_inputs_and_results() -> None:
    for case in _cases():
        state = CalculatorState(itinerary_name=case["name"], number_of_pax=7, rows=_rows(case))
        restored = calculator_state_from_dict(calculator_state_to_dict(state))

        assert restored == state
        assert calculate_rows(restored.rows, case["rates"]) == calculate_rows(state.rows, case["rates"])
        assert calculate_totals(restored.rows, case["rates"]) == calculate_totals(state.rows, case["rates"])


def test_excel_round_trip_preserves_financial_results_and_formula_inputs() -> None:
    for case in _cases():
        state = CalculatorState(itinerary_name=case["name"], rows=_rows(case))
        exported = export_calculation_workbook(state, currency_rates=case["rates"])
        imported = import_calculation_workbook(exported.content, filename=exported.filename)

        assert calculate_rows(imported.state.rows, imported.currency_rates) == calculate_rows(state.rows, case["rates"])
        assert calculate_totals(imported.state.rows, imported.currency_rates) == calculate_totals(state.rows, case["rates"])
        for original, restored in zip(state.rows, imported.state.rows):
            for field_name in original.__dataclass_fields__:
                original_value = getattr(original, field_name)
                restored_value = getattr(restored, field_name)
                if field_name == "sales_price_per_unit" and original_value == 0:
                    assert restored_value is None
                else:
                    assert restored_value == original_value, (case["name"], field_name)


def test_excel_export_applies_canonical_precision_to_rates_overrides_and_totals() -> None:
    case = next(item for item in _cases() if item["name"] == "manual_formula_overrides_and_rate_precision")
    exported = export_calculation_workbook(
        CalculatorState(rows=_rows(case)),
        currency_rates=case["rates"],
    )
    workbook = load_workbook(BytesIO(exported.content), data_only=False)
    sheet = workbook["Kalk"]
    currency = workbook["Curr"]

    assert currency["C3"].value == 11.123457
    assert currency["C4"].value == 9.876543
    assert sheet["U7"].value == "=ROUND((S7*0.812345678),2)"
    assert sheet["W7"].value == "=ROUND((10/3),6)"
    assert sheet["X7"].value == "=ROUND((U7*W7+0.005),2)"
    assert sheet["AB7"].value == "=ROUND((29/3),6)"
    assert sheet["AC7"].value == "=ROUND((Z7*AB7+0.005),2)"
    assert sheet["AD7"].value == "=ROUND((AC7-X7+0.005),2)"
    assert sheet["AE7"].value == "=ROUND((1/3),6)"
    for reference, formula in TOTAL_FORMULAS.items():
        assert sheet[reference].value == formula


def test_margin_shortcut_uses_actual_net_cost_and_target_gp_definition() -> None:
    rows = (
        CalculatorRow(
            row_id="1",
            gross_price_per_unit=100,
            units=2,
            supplier_commission=0.2,
            supplier_currency="EUR",
            sales_currency="USD",
            net_price_nok_override="=U7*W7+10",
        ),
    )
    rates = {"NOK": 1, "EUR": 12, "USD": 10}
    target = 0.15

    sales_price = sales_price_per_unit_for_margin(rows, 0, target, rates)
    updated = rows[0].with_changes(sales_price_per_unit=sales_price)
    calculated = calculate_rows((updated,), rates)[0]

    assert calculated.gp_percent == pytest.approx(target, abs=0.00001)
    assert sales_price == pytest.approx(calculated.net_price_nok / (2 * 10 * (1 - target)))


def test_financial_fixture_rows_are_json_safe_dataclass_inputs() -> None:
    for case in _cases():
        assert [asdict(row) for row in _rows(case)]
