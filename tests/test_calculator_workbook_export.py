from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import load_workbook

from calculator.calculator_state import CalculatorState
from calculator.columns import ADVANCED_COLUMN_RANGES, DATA_END_ROW, DATA_START_ROW
from calculator.formula_map import PAYMENT_FORMULAS, TOTAL_FORMULAS, expected_row_formulas
from calculator.filename_sanitizer import calculation_workbook_filename, sanitize_filename_stem
from calculator.row_model import CalculatorRow
from calculator.template_structure import inspect_template_structure
from calculator.workbook_export import (
    build_calculation_workbook,
    export_calculation_workbook,
    save_calculation_workbook,
)


def test_filename_sanitizer_creates_windows_safe_calculation_name() -> None:
    assert sanitize_filename_stem(' Tromsø: Northern/ Lights? 2026. ') == "Tromsø Northern Lights 2026"
    assert sanitize_filename_stem("   ") == "Itinerary"
    assert calculation_workbook_filename("Tromsø Northern Lights 2026") == "Tromsø Northern Lights 2026 - Calculation.xlsx"


def test_build_workbook_fills_rows_and_preserves_core_formulas() -> None:
    state = CalculatorState(
        itinerary_name="Tromsø Northern Lights 2026",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Hotel",
                from_date="01/10/2026",
                to_date="02/10/2026",
                supplier="Scandic",
                travel_element="Scandic Simonkenttä",
                manual_booking=True,
                status="Booked",
                comments="Breakfast included",
                non_refundable=True,
                refundable=False,
                url="https://example.com/hotel",
                gross_price_per_unit=100,
                units=2,
                supplier_commission=0.1,
                supplier_currency="eur",
                sales_price_per_unit=150,
                sales_currency="nok",
                vat25=10,
                vat15=1,
            ),
            CalculatorRow(
                row_id="2",
                day="Day 2",
                type="Activity",
                travel_element="Northern lights tour",
                gross_price_per_unit=50,
                units=4,
                supplier_commission=0,
                supplier_currency="NOK",
                sales_currency="NOK",
                vat12=2,
                vat0_domestic=3,
                vat0_international=4,
            ),
        ),
    )

    workbook = build_calculation_workbook(state)
    sheet = workbook["Kalk"]

    assert sheet["B7"].value == "1"
    assert sheet["C7"].value == "Day 1"
    assert sheet["D7"].value == "Hotel"
    assert sheet["E7"].value == "01/10/2026"
    assert sheet["F7"].value == "02/10/2026"
    assert sheet["I7"].value == "Scandic"
    assert sheet["J7"].value == "Scandic Simonkenttä"
    assert sheet["K7"].value is True
    assert sheet["L7"].value == "Booked"
    assert sheet["M7"].value == "Breakfast included"
    assert sheet["N7"].value is True
    assert sheet["O7"].value is False
    assert sheet["P7"].value == "https://example.com/hotel"
    assert sheet["Q7"].value == 100
    assert sheet["R7"].value == 2
    assert sheet["T7"].value == 0.1
    assert sheet["V7"].value == "EUR"
    assert sheet["Y7"].value == 150
    assert sheet["AA7"].value == "NOK"
    assert sheet["AF7"].value == 10
    assert sheet["AG7"].value == 1

    assert sheet["B8"].value == "2"
    assert sheet["J8"].value == "Northern lights tour"
    assert sheet["Y8"].value == "=Q8"

    expected = expected_row_formulas(7)
    for column, formula in expected.items():
        if column in {"Y", "W", "AB"}:
            continue
        assert sheet[f"{column}7"].value == formula
    assert sheet["W7"].value == 11
    assert sheet["AB7"].value == 1

    assert sheet["Z101"].value == TOTAL_FORMULAS["Z101"]
    assert sheet["AC101"].value == TOTAL_FORMULAS["AC101"]
    assert sheet["Z103"].value == "=Z101"
    assert sheet["Z104"].value == PAYMENT_FORMULAS["Z104"]


def test_exported_workbook_preserves_template_structure_and_styles() -> None:
    state = CalculatorState(
        itinerary_name="Export Test",
        rows=(CalculatorRow(row_id="1", travel_element="Styled line", gross_price_per_unit=10, units=1),),
    )

    export = export_calculation_workbook(state)
    workbook = load_workbook(BytesIO(export.content), data_only=False)
    sheet = workbook["Kalk"]

    assert export.filename == "Export Test - Calculation.xlsx"
    assert workbook.sheetnames == ["Curr", "Kalk"]
    assert sheet.auto_filter.ref == "B6:AE101"
    assert inspect_template_structure().hidden_column_ranges == ADVANCED_COLUMN_RANGES
    assert sheet.column_dimensions["G"].hidden is True
    assert sheet.column_dimensions["G"].outlineLevel == 1
    assert sheet.column_dimensions["J"].collapsed is True
    assert sheet.column_dimensions["P"].collapsed is True
    assert sheet.sheet_view.showOutlineSymbols is True
    assert sheet["B6"].value == "ID"
    assert sheet["B6"].fill.fill_type is not None
    assert sheet["S7"].value == "=+Q7*R7"


def test_save_calculation_workbook_writes_xlsx_file(tmp_path) -> None:
    state = CalculatorState(
        itinerary_name="Oslo Fjord",
        rows=(CalculatorRow(row_id="1", travel_element="Fjord cruise", gross_price_per_unit=10, units=2),),
    )

    output_path = save_calculation_workbook(state, tmp_path)

    assert output_path.name == "Oslo Fjord - Calculation.xlsx"
    workbook = load_workbook(output_path, data_only=False)
    assert workbook["Kalk"]["J7"].value == "Fjord cruise"


def test_export_rejects_more_rows_than_template_can_hold() -> None:
    rows = tuple(CalculatorRow(row_id=str(index)) for index in range(DATA_START_ROW, DATA_END_ROW + 2))

    with pytest.raises(ValueError, match="at most 93 rows"):
        build_calculation_workbook(CalculatorState(rows=rows))


def test_exported_workbook_writes_default_currency_table_and_xrates() -> None:
    state = CalculatorState(
        itinerary_name="Currency Test",
        rows=(
            CalculatorRow(row_id="1", gross_price_per_unit=100, units=1, supplier_currency="EUR", sales_currency="USD"),
            CalculatorRow(row_id="2", gross_price_per_unit=100, units=1, supplier_currency="NOK", sales_currency="GBP"),
        ),
    )

    workbook = build_calculation_workbook(state)
    curr = workbook["Curr"]
    sheet = workbook["Kalk"]

    assert curr["B2"].value == "NOK"
    assert curr["C2"].value == 1
    assert curr["B3"].value == "EUR"
    assert curr["C3"].value == 11
    assert curr["B4"].value == "USD"
    assert curr["C4"].value == 10
    assert sheet["W7"].value == 11
    assert sheet["AB7"].value == 10
    assert sheet["W8"].value == 1
    assert sheet["AB8"].value == 13
