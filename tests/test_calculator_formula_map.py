from __future__ import annotations

import pytest

from calculator.formula_map import (
    PAYMENT_FORMULAS,
    ROW_FORMULA_COLUMNS,
    TOTAL_FORMULAS,
    expected_row_formulas,
    inspect_formula_map,
    validate_formula_map,
)


def test_expected_formula_map_for_first_data_row() -> None:
    assert expected_row_formulas(7) == {
        "S": "=+Q7*R7",
        "U": "=S7*(1-T7)",
        "W": "=IFERROR(VLOOKUP(V7,Curr!$B$2:$C$13,2,FALSE),0)",
        "X": "=U7*W7",
        "Y": "=Q7",
        "Z": "=+Y7*R7",
        "AB": "=IFERROR(VLOOKUP(AA7,Curr!$B$2:$C$13,2,FALSE),0)",
        "AC": "=+Y7*AB7*R7",
        "AD": "=+AC7-X7",
        "AE": "=IFERROR(AD7/AC7,0)",
    }


def test_expected_formula_map_rejects_non_data_rows() -> None:
    with pytest.raises(ValueError):
        expected_row_formulas(6)

    with pytest.raises(ValueError):
        expected_row_formulas(100)


def test_template_formula_map_matches_representative_rows() -> None:
    formula_map = inspect_formula_map()

    assert tuple(formula_map.row_formulas[7]) == ROW_FORMULA_COLUMNS
    assert formula_map.row_formulas[7] == expected_row_formulas(7)
    assert formula_map.row_formulas[8] == expected_row_formulas(8)
    assert formula_map.row_formulas[99] == expected_row_formulas(99)


def test_template_totals_and_payment_formulas_are_locked() -> None:
    formula_map = inspect_formula_map()

    assert formula_map.total_formulas == TOTAL_FORMULAS
    assert formula_map.payment_formulas == PAYMENT_FORMULAS


def test_formula_map_validator_accepts_bundled_template() -> None:
    assert validate_formula_map() == ()
