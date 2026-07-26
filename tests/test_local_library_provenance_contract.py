from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

from app_modules.calculator_component_payload import build_calculator_grid_payload
from app_modules.calculator_generation_rows import parse_and_normalize_calculator_rows
from app_modules.calculator_grid_data import table_data_to_rows
from calculator.calculator_state import CalculatorState
from calculator.library_model import LocalLibraryRow
from calculator.library_normalize import library_row_to_calculator_row
from calculator.library_store import LocalLibraryReadResult
from calculator.row_model import CalculatorRow
from calculator.state_serialization import calculator_state_from_dict, calculator_state_to_dict
from calculator.to_itinerary_input import calculator_state_to_raw_input
from calculator.workbook_export import export_calculation_workbook
from calculator.workbook_provenance import CUSTOM_PROPERTY_NAME
from itinerary_generation.render_document_builder import build_render_document
from shared.source_rows import row_ids_for_rows


def _sourced_row(row_id: str, library_id: str, source_row: int) -> CalculatorRow:
    return CalculatorRow(
        row_id=row_id,
        day="Day 1",
        type="Activity",
        travel_element="Rovaniemi: Same Northern Lights Hunt",
        url=f"https://supplier.invalid/{source_row}",
        gross_price_per_unit=100,
        units=1,
        library_id=library_id,
        source_workbook="Calculation-template-Inputs-fixed-outline-restored.xlsx",
        source_sheet="Activities",
        source_row=source_row,
    )


def test_library_selection_projection_keeps_source_identity() -> None:
    source = LocalLibraryRow(
        library_id="activity-row-19",
        source_workbook="library.xlsx",
        source_sheet="Activities",
        source_row=19,
        type="Activity",
        travel_element="Northern Lights Hunt",
    )
    row = library_row_to_calculator_row(source, row_id="7")
    assert (row.library_id, row.source_workbook, row.source_sheet, row.source_row) == (
        "activity-row-19", "library.xlsx", "Activities", 19,
    )


def test_component_payload_transports_workbook_provenance_separately_from_display_data() -> None:
    source = LocalLibraryRow(
        library_id="activity-row-19",
        source_workbook="library.xlsx",
        source_sheet="Activities",
        source_row=19,
        type="Activity",
        travel_element="Northern Lights Hunt",
    )
    payload = build_calculator_grid_payload(
        CalculatorState(),
        LocalLibraryReadResult((source,), "local_excel", True, fingerprint="fixture"),
    )
    compact = payload["library_rows"][0]
    assert compact["i"] == "activity-row-19"
    assert compact["b"] == "library.xlsx"
    assert compact["w"] == "Activities"
    assert compact["x"] == 19
    assert payload["library_payload_version"] == "compact-v3"


def test_hidden_provenance_survives_grid_round_trip_and_saved_project_state() -> None:
    original = _sourced_row("1", "activity-row-19", 19)
    edited = table_data_to_rows(
        ({"row_id": "1", "travel_element": "Edited title"},),
        previous_rows=(original,),
    )[0]
    assert (edited.library_id, edited.source_sheet, edited.source_row) == ("activity-row-19", "Activities", 19)

    restored = calculator_state_from_dict(calculator_state_to_dict(CalculatorState(rows=(edited,))))
    restored_row = restored.rows[0]
    assert (restored_row.library_id, restored_row.source_workbook, restored_row.source_sheet, restored_row.source_row) == (
        "activity-row-19", "Calculation-template-Inputs-fixed-outline-restored.xlsx", "Activities", 19,
    )


def test_identical_selected_products_remain_distinct_through_generation_and_render_identity() -> None:
    parsed = parse_and_normalize_calculator_rows((
        _sourced_row("1", "activity-row-19", 19),
        _sourced_row("2", "activity-row-20", 20),
    ))
    assert len(parsed) == 2
    assert [row["library_id"] for row in parsed] == ["activity-row-19", "activity-row-20"]
    assert [row["source_row"] for row in parsed] == [19, 20]
    source_ids = row_ids_for_rows(parsed)
    assert len(set(source_ids)) == 2
    assert all(row["source_url"].startswith("https://supplier.invalid/") for row in parsed)

    render_document = build_render_document(parsed)
    assert len(render_document.days) == 1
    assert set(render_document.days[0].source_row_ids) == set(source_ids)


def test_urls_remain_internal_metadata_and_do_not_enter_generator_copy() -> None:
    state = CalculatorState(rows=(_sourced_row("1", "activity-row-19", 19),))
    assert "supplier.invalid" not in calculator_state_to_raw_input(state)
    parsed = parse_and_normalize_calculator_rows(state.rows)
    assert parsed[0]["source_url"] == "https://supplier.invalid/19"
    assert "supplier.invalid" not in parsed[0]["title"]


def test_excel_export_carries_internal_provenance_custom_property() -> None:
    state = CalculatorState(rows=(_sourced_row("1", "activity-row-19", 19),))
    export = export_calculation_workbook(state)
    assert len(export.source_provenance) == 1
    assert export.source_provenance[0].source_sheet == "Activities"
    assert export.source_provenance[0].source_row == 19

    with ZipFile(BytesIO(export.content)) as package:
        xml = package.read("docProps/custom.xml").decode("utf-8")
    assert CUSTOM_PROPERTY_NAME in xml
    assert "activity-row-19" in xml
    assert "Activities" in xml
    assert "supplier.invalid/19" in xml


def test_backend_component_rerender_keeps_hidden_calculator_provenance() -> None:
    row = _sourced_row("1", "activity-row-19", 19)
    payload = build_calculator_grid_payload(
        CalculatorState(rows=(row,)),
        LocalLibraryReadResult((), "local_excel", True, fingerprint="fixture"),
    )

    backend_row = payload["rows"][0]
    assert backend_row["library_id"] == "activity-row-19"
    assert backend_row["source_workbook"] == "Calculation-template-Inputs-fixed-outline-restored.xlsx"
    assert backend_row["source_sheet"] == "Activities"
    assert backend_row["source_row"] == 19
