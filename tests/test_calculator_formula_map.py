from __future__ import annotations

import pytest
from zipfile import ZipFile

from calculator.formula_map import (
    PAYMENT_FORMULAS,
    ROW_FORMULA_COLUMNS,
    TOTAL_FORMULAS,
    expected_row_formulas,
    inspect_formula_map,
    validate_formula_map,
)

from calculator.calculator_state import CalculatorState
from calculator.template_structure import default_template_path
from calculator.workbook_export import export_calculation_workbook

def test_expected_formula_map_for_first_data_row() -> None:
    assert expected_row_formulas(7) == {
        "S": "=ROUND(Q7*R7,2)",
        "U": "=ROUND(S7*(1-T7),2)",
        "W": "=IFERROR(VLOOKUP(V7,Curr!$B$2:$C$13,2,FALSE),0)",
        "X": "=ROUND(U7*W7,2)",
        "Y": "=IFERROR(Q7*W7/AB7,0)",
        "Z": "=ROUND(Y7*R7,2)",
        "AB": "=IFERROR(VLOOKUP(AA7,Curr!$B$2:$C$13,2,FALSE),0)",
        "AC": "=ROUND(Z7*AB7,2)",
        "AD": "=ROUND(AC7-X7,2)",
        "AE": "=IFERROR(AD7/AC7,0)",
    }


def test_expected_formula_map_rejects_non_data_rows() -> None:
    with pytest.raises(ValueError):
        expected_row_formulas(6)

    with pytest.raises(ValueError):
        expected_row_formulas(100)


def _export_path(tmp_path):
    path = tmp_path / "canonical-export.xlsx"
    path.write_bytes(export_calculation_workbook(CalculatorState()).content)
    return path


def test_export_formula_map_matches_representative_rows(tmp_path) -> None:
    path = _export_path(tmp_path)
    formula_map = inspect_formula_map(path)

    assert tuple(formula_map.row_formulas[7]) == ROW_FORMULA_COLUMNS
    assert formula_map.row_formulas[7] == expected_row_formulas(7)
    assert formula_map.row_formulas[8] == expected_row_formulas(8)
    assert formula_map.row_formulas[99] == expected_row_formulas(99)


def test_export_totals_and_payment_formulas_are_locked(tmp_path) -> None:
    formula_map = inspect_formula_map(_export_path(tmp_path))

    assert formula_map.total_formulas == TOTAL_FORMULAS
    assert formula_map.payment_formulas == PAYMENT_FORMULAS


def test_formula_map_validator_accepts_generated_export(tmp_path) -> None:
    assert validate_formula_map(_export_path(tmp_path)) == ()


def test_bundled_template_preserves_excel_package_metadata() -> None:
    with ZipFile(default_template_path()) as workbook_package:
        names = set(workbook_package.namelist())

    assert {
        "customXml/item1.xml",
        "xl/calcChain.xml",
        "xl/printerSettings/printerSettings1.bin",
        "xl/sharedStrings.xml",
        "xl/worksheets/_rels/sheet2.xml.rels",
    } <= names
