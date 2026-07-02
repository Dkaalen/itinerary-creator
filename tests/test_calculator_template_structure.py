from __future__ import annotations

from calculator.columns import (
    ADVANCED_COLUMN_RANGES,
    AUTO_FILTER_REF,
    COLUMN_SPECS,
    DATA_END_ROW,
    DATA_START_ROW,
    HEADER_BY_LETTER,
    HEADER_ROW,
    PAYMENT_END_ROW,
    PAYMENT_START_ROW,
    TOTALS_ROW,
    column_letters,
    get_column_by_key,
    get_column_by_letter,
    headers,
)
from calculator.template_structure import (
    default_template_path,
    inspect_template_structure,
    validate_template_structure,
)


def test_bundled_calculation_template_exists() -> None:
    assert default_template_path().is_file()


def test_calculator_column_contract_matches_template_headers() -> None:
    assert column_letters()[0] == "B"
    assert column_letters()[-1] == "AJ"
    assert len(column_letters()) == 35
    assert headers()[0] == "ID"
    assert headers()[-1] == "VAT0-I"
    assert get_column_by_letter("J").key == "travel_element"
    assert get_column_by_key("sales_price_nok_total").letter == "AC"


def test_template_structure_matches_locked_layout() -> None:
    structure = inspect_template_structure()

    assert structure.sheet_names == ("Curr", "Kalk")
    assert structure.active_sheet == "Kalk"
    assert structure.kalk_max_column == 36
    assert structure.header_row == HEADER_ROW == 6
    assert structure.data_start_row == DATA_START_ROW == 7
    assert structure.data_end_row == DATA_END_ROW == 99
    assert structure.totals_row == TOTALS_ROW == 101
    assert structure.payment_start_row == PAYMENT_START_ROW == 103
    assert structure.payment_end_row == PAYMENT_END_ROW == 111
    assert structure.workbook_start_column == "B"
    assert structure.workbook_end_column == "AJ"
    assert structure.auto_filter_ref == AUTO_FILTER_REF
    assert structure.headers_by_letter == HEADER_BY_LETTER
    assert structure.hidden_column_ranges == ADVANCED_COLUMN_RANGES
    assert structure.grouped_column_ranges == ADVANCED_COLUMN_RANGES
    assert structure.collapsed_column_markers == ("J", "P")


def test_template_currency_table_is_available() -> None:
    structure = inspect_template_structure()

    assert structure.currencies == {
        "EUR": 11.3,
        "SEK": 1.02,
        "DKK": 1.5,
        "ISK": 0.075,
        "NOK": 1.0,
        "USD": 10.6,
    }


def test_template_structure_validator_accepts_bundled_template() -> None:
    assert validate_template_structure() == ()


def test_formula_columns_are_tracked_as_formula_columns() -> None:
    formula_columns = tuple(column.letter for column in COLUMN_SPECS if column.is_formula)

    assert formula_columns == ("S", "U", "W", "X", "Y", "Z", "AB", "AC", "AD", "AE")
