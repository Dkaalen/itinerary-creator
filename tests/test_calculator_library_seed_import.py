from __future__ import annotations

from openpyxl import Workbook

from calculator.library_fixture import fallback_library_rows
from calculator.library_model import LOCAL_LIBRARY_HEADERS, LocalLibraryRow
from calculator.library_normalize import (
    clean_formula_text,
    library_row_to_calculator_row,
    normalize_library_mapping,
)
from calculator.library_seed_import import import_cheat_sheet_workbook, import_local_library_workbook


def test_local_library_headers_match_google_ready_schema() -> None:
    assert LOCAL_LIBRARY_HEADERS[:11] == (
        "schema_version",
        "library_id",
        "is_deleted",
        "is_fetchable",
        "record_type",
        "source_workbook",
        "source_sheet",
        "source_row",
        "country",
        "category",
        "search_text",
    )
    assert LOCAL_LIBRARY_HEADERS[11:46] == (
        "ID",
        "Day",
        "Type",
        "From date",
        "To date",
        "From time",
        "To time",
        "Supplier",
        "Travel element",
        "Manual booking?",
        "Status",
        "Comments",
        "Non-refundable",
        "Refundable",
        "URL",
        "Gross P per unit",
        "Units",
        "Gross P",
        "Supp Comm",
        "Net P",
        "Supp curr",
        "X-rate",
        "Net P NOK",
        "Sales P per unit",
        "Price",
        "Sales curr",
        "X-rate Sales",
        "Sales P NOK tot",
        "GP NOK",
        "GP %",
        "VAT25",
        "VAT15",
        "VAT12",
        "VAT0-D",
        "VAT0-I",
    )


def test_normalize_library_mapping_coerces_types_and_preserves_formula_text() -> None:
    row = normalize_library_mapping(
        {
            "library_id": "fi_8_73567a78",
            "is_deleted": "FALSE",
            "is_fetchable": "TRUE",
            "record_type": "line",
            "source_sheet": "FI",
            "source_row": "8",
            "country": "fi",
            "category": "Arrival",
            "Type": "Arrival",
            "Travel element": "Helsinki: Welcome to Finland",
            "Gross P per unit": "25,5",
            "Units": "2",
            "Supp Comm": "0.15",
            "Supp curr": "eur",
            "Sales P per unit": "30",
            "Sales curr": "nok",
            "Manual booking?": "YES",
            "Non-refundable": "x",
            "formula_supplier_xrate": "'IFERROR(VLOOKUP(V8,[1]Curr!$B$2:$C$13,2,FALSE),0)",
        }
    )

    assert row.library_id == "fi_8_73567a78"
    assert row.is_available_for_fetch is True
    assert row.source_row == 8
    assert row.gross_price_per_unit == 25.5
    assert row.units == 2.0
    assert row.supplier_commission == 0.15
    assert row.supplier_currency == "EUR"
    assert row.sales_price_per_unit == 30.0
    assert row.sales_currency == "NOK"
    assert row.manual_booking is True
    assert row.non_refundable is True
    assert row.formula_supplier_xrate == "IFERROR(VLOOKUP(V8,Curr!$B$2:$C$13,2,FALSE),0)"
    assert "Helsinki: Welcome to Finland" in row.search_text


def test_clean_formula_text_removes_old_external_currency_workbook_reference() -> None:
    assert clean_formula_text("'[1]Curr'!$B$2:$C$13") == "Curr!$B$2:$C$13"
    assert clean_formula_text("'[Old.xlsx]Curr'!$B$2:$C$13") == "Curr!$B$2:$C$13"


def test_import_local_library_workbook_reads_google_ready_rows(tmp_path) -> None:
    workbook_path = tmp_path / "local_library.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Local Library"
    sheet.append(LOCAL_LIBRARY_HEADERS)
    sheet.append(_local_library_values(library_id="lib_1", fetchable="TRUE", travel_element="Oslo hotel"))
    sheet.append(_local_library_values(library_id="lib_2", fetchable="FALSE", travel_element="Hidden row"))
    workbook.save(workbook_path)

    rows = import_local_library_workbook(workbook_path)

    assert len(rows) == 2
    assert rows[0].library_id == "lib_1"
    assert rows[0].travel_element == "Oslo hotel"
    assert rows[0].is_available_for_fetch is True
    assert rows[1].is_available_for_fetch is False


def test_import_cheat_sheet_workbook_enriches_source_metadata(tmp_path) -> None:
    workbook_path = tmp_path / "Cheat Sheet 2.0.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "FI"
    for _ in range(5):
        sheet.append([])
    sheet.append(["ID", "Day", "Type", "Supplier", "Travel element", "Gross P per unit", "Units", "Supp curr"])
    sheet.append(["Helsinki", "All year", "Activity", "Finntastic", "Helsinki walking tour", 25, 1, "EUR"])
    workbook.save(workbook_path)

    rows = import_cheat_sheet_workbook(workbook_path)

    assert len(rows) == 1
    assert rows[0].source_workbook == "Cheat Sheet 2.0.xlsx"
    assert rows[0].source_sheet == "FI"
    assert rows[0].country == "FI"
    assert rows[0].category == "Activity"
    assert rows[0].travel_element == "Helsinki walking tour"
    assert rows[0].gross_price_per_unit == 25.0


def test_library_row_can_be_converted_to_calculator_row_without_metadata() -> None:
    library_row = LocalLibraryRow(
        library_id="lib_1",
        type="Activity",
        supplier="Supplier",
        travel_element="Tour",
        gross_price_per_unit=50,
        units=2,
        supplier_currency="EUR",
        sales_price_per_unit=75,
        sales_currency="NOK",
    )

    calculator_row = library_row_to_calculator_row(library_row, row_id="7")

    assert calculator_row.row_id == "7"
    assert calculator_row.type == "Activity"
    assert calculator_row.supplier == "Supplier"
    assert calculator_row.travel_element == "Tour"
    assert calculator_row.gross_price_per_unit == 50
    assert calculator_row.sales_price_per_unit == 75


def test_fallback_fixture_uses_bundled_cheat_sheet_rows() -> None:
    rows = fallback_library_rows()
    fetchable_rows = [row for row in rows if row.is_available_for_fetch]

    assert len(rows) >= 400
    assert len(fetchable_rows) >= 350
    assert any("Finntastic Walking Tour" in row.travel_element for row in fetchable_rows)
    assert any(row.source_sheet == "NO" for row in fetchable_rows)
    assert any(row.source_sheet == "FI" for row in fetchable_rows)
    assert all(row.updated_by == "bundled_cheat_sheet" for row in rows)


def _local_library_values(library_id: str, fetchable: str, travel_element: str) -> list[object]:
    values = {header: "" for header in LOCAL_LIBRARY_HEADERS}
    values.update(
        {
            "schema_version": "local_library_v1",
            "library_id": library_id,
            "is_deleted": "FALSE",
            "is_fetchable": fetchable,
            "record_type": "line",
            "source_workbook": "Cheat Sheet 2.0.xlsx",
            "source_sheet": "NO",
            "source_row": "7",
            "country": "NO",
            "category": "Hotel",
            "Type": "Hotel",
            "Travel element": travel_element,
            "Gross P per unit": "100",
            "Units": "1",
            "Supp curr": "EUR",
            "Sales curr": "EUR",
        }
    )
    return [values[header] for header in LOCAL_LIBRARY_HEADERS]
