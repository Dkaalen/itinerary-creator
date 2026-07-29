from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app_modules.calculator_backup_action import read_calculator_upload
from calculator.calculations import calculate_totals
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.workbook_export import export_calculation_workbook
from calculator.workbook_import import import_calculation_workbook


class UploadedWorkbook(BytesIO):
    name = "Nordic Round Trip - Calculation.xlsx"


def test_export_import_round_trip_preserves_calculation_and_rates() -> None:
    rates = {"NOK": 1.0, "EUR": 12.25, "USD": 10.5}
    state = CalculatorState(
        itinerary_name="Nordic Round Trip",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                type="Hotel",
                travel_element="Oslo hotel",
                gross_price_per_unit=100,
                units=2,
                supplier_commission=0.2,
                supplier_currency="EUR",
                sales_price_per_unit=150,
                sales_currency="NOK",
                vat25=25,
            ),
            CalculatorRow(
                row_id="2",
                day="Day 2",
                type="Activity",
                travel_element="Museum",
                gross_price_per_unit="=S7/4",
                units=3,
                supplier_currency="NOK",
                sales_currency="USD",
                price_override="=$Q$7*R8",
            ),
        ),
    )

    exported = export_calculation_workbook(state, currency_rates=rates)
    imported = import_calculation_workbook(exported.content, filename=exported.filename)

    assert imported.state.itinerary_name == "Nordic Round Trip"
    assert imported.currency_rates["EUR"] == 12.25
    assert imported.currency_rates["USD"] == 10.5
    assert imported.state.rows[0].travel_element == "Oslo hotel"
    assert imported.state.rows[0].supplier_commission == 0.2
    assert imported.state.rows[1].gross_price_per_unit == "=S7/4"
    assert imported.state.rows[1].price_override == "=$Q$7*R8"
    assert calculate_totals(imported.state.rows, imported.currency_rates) == calculate_totals(state.rows, rates)


def test_streamlit_upload_reader_recognizes_excel_and_returns_rates() -> None:
    state = CalculatorState(rows=(CalculatorRow(row_id="1", gross_price_per_unit=10, units=2),))
    exported = export_calculation_workbook(state, currency_rates={"NOK": 1, "EUR": 12})
    upload = UploadedWorkbook(exported.content)

    imported = read_calculator_upload(upload)

    assert imported.source == "xlsx"
    assert imported.state.itinerary_name == "Nordic Round Trip"
    assert imported.state.rows[0].gross_price_per_unit == 10
    assert imported.currency_rates and imported.currency_rates["EUR"] == 12


def test_reference_template_can_be_imported_without_creating_fake_rows() -> None:
    template = Path(__file__).resolve().parents[1] / "calculator" / "templates" / "Calculation-template-Mal.xlsx"

    imported = import_calculation_workbook(template.read_bytes(), filename=template.name)

    assert imported.state.rows == ()
    assert imported.currency_rates["NOK"] == 1


def test_export_import_keeps_converted_default_sales_price_automatic() -> None:
    rates = {"NOK": 1, "EUR": 12}
    state = CalculatorState(
        itinerary_name="Converted Sales",
        rows=(
            CalculatorRow(
                row_id="1",
                gross_price_per_unit=1200,
                units=1,
                supplier_currency="NOK",
                sales_currency="EUR",
            ),
        ),
    )

    exported = export_calculation_workbook(state, currency_rates=rates)
    imported = import_calculation_workbook(exported.content, filename=exported.filename)

    assert imported.state.rows[0].sales_price_per_unit is None
    totals = calculate_totals(imported.state.rows, imported.currency_rates)
    assert totals.sales_price_nok_total == 1200
    assert totals.gp_nok == 0


def test_export_import_preserves_trip_start_and_locked_date_relationships() -> None:
    state = CalculatorState(
        itinerary_name="Dynamic dates",
        trip_start_date="2026-02-01",
        rows=(
            CalculatorRow(
                row_id="1",
                day="Day 1",
                from_date="01.02.2026",
                from_date_mode="linked",
                from_date_offset=0,
            ),
            CalculatorRow(
                row_id="2",
                day="Day 2",
                from_date="10.02.2026",
                from_date_mode="locked",
                to_date="12.02.2026",
                to_date_mode="linked",
                to_date_offset=11,
            ),
        ),
    )

    exported = export_calculation_workbook(state, currency_rates={"NOK": 1, "EUR": 12})
    imported = import_calculation_workbook(exported.content, filename=exported.filename)

    assert imported.state.trip_start_date == "2026-02-01"
    assert imported.state.rows[0].from_date_mode == "linked"
    assert imported.state.rows[0].from_date_offset == 0
    assert imported.state.rows[1].from_date_mode == "locked"
    assert imported.state.rows[1].from_date_offset is None
    assert imported.state.rows[1].to_date_mode == "linked"
    assert imported.state.rows[1].to_date_offset == 11
