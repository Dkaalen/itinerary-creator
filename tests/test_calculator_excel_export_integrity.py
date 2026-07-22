from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from openpyxl import load_workbook

from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.workbook_export import build_calculation_workbook, export_calculation_workbook
from calculator.workbook_export_plan import build_workbook_export_plan


def _state() -> CalculatorState:
    return CalculatorState(rows=(
        CalculatorRow(row_id="internal-arrival", day="Day 1", type="Arrival", travel_element="Welcome", units=1),
        CalculatorRow(row_id="internal-hotel", day="Day 1", type="Hotel", travel_element="Hotel", gross_price_per_unit=200, units=2),
        CalculatorRow(row_id="internal-leisure", day="Day 2", type="Leisure", travel_element="Free time", units=1),
        CalculatorRow(row_id="internal-activity", day="Day 2", type="Activity", travel_element="Tour", gross_price_per_unit=50, units=2),
    ))


def test_column_b_is_cost_only_chronological_line_number() -> None:
    plan = build_workbook_export_plan(_state(), {"NOK": 1, "EUR": 11})
    cells = plan.calculator_cell_map()
    assert cells["B7"].value is None
    assert cells["B8"].value == 1
    assert cells["B9"].value is None
    assert cells["B10"].value == 2
    assert "internal-hotel" not in {cell.value for cell in plan.calculator_cells}


def test_export_keeps_last_used_row_plus_ten_visible() -> None:
    state = _state()
    plan = build_workbook_export_plan(state)
    assert plan.visible_data_end_row == 20

    mutable = build_calculation_workbook(state)
    sheet = mutable["Kalk"]
    assert sheet.row_dimensions[20].hidden is False
    assert sheet.row_dimensions[21].hidden is True
    assert sheet.row_dimensions[99].hidden is True
    assert sheet.row_dimensions[101].hidden is False

    downloaded = load_workbook(BytesIO(export_calculation_workbook(state).content), data_only=False)
    downloaded_sheet = downloaded["Kalk"]
    assert downloaded_sheet.row_dimensions[20].hidden is False
    assert downloaded_sheet.row_dimensions[21].hidden is True
    assert downloaded_sheet.row_dimensions[99].hidden is True
    assert downloaded_sheet.row_dimensions[101].hidden is False


def test_export_removes_stale_calculation_chain_and_references() -> None:
    content = export_calculation_workbook(_state()).content
    with ZipFile(BytesIO(content)) as archive:
        assert "xl/calcChain.xml" not in archive.namelist()
        relationships = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        content_types = archive.read("[Content_Types].xml").decode("utf-8")
    assert "calcChain" not in relationships
    assert "calcChain" not in content_types
