"""Column definitions for the calculation workbook."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculatorColumn:
    """One locked column in the Kalk worksheet."""

    key: str
    letter: str
    header: str
    index: int
    is_advanced: bool = False
    is_formula: bool = False


HEADER_ROW = 6
DATA_START_ROW = 7
DATA_END_ROW = 99
TOTALS_ROW = 101
PAYMENT_START_ROW = 103
PAYMENT_END_ROW = 111
WORKBOOK_START_COLUMN = "B"
WORKBOOK_END_COLUMN = "AJ"
AUTO_FILTER_REF = "B6:AE101"
CURRENCY_LOOKUP_RANGE = "Curr!$B$2:$C$13"
KALK_SHEET_NAME = "Kalk"
CURRENCY_SHEET_NAME = "Curr"

COLUMN_SPECS: tuple[CalculatorColumn, ...] = (
    CalculatorColumn("id", "B", "ID", 2),
    CalculatorColumn("day", "C", "Day", 3),
    CalculatorColumn("type", "D", "Type", 4),
    CalculatorColumn("from_date", "E", "From date", 5),
    CalculatorColumn("to_date", "F", "To date", 6),
    CalculatorColumn("from_time", "G", "From time", 7, is_advanced=True),
    CalculatorColumn("to_time", "H", "To time", 8, is_advanced=True),
    CalculatorColumn("supplier", "I", "Supplier", 9, is_advanced=True),
    CalculatorColumn("travel_element", "J", "Travel element", 10),
    CalculatorColumn("manual_booking", "K", "Manual booking?", 11, is_advanced=True),
    CalculatorColumn("status", "L", "Status", 12, is_advanced=True),
    CalculatorColumn("comments", "M", "Comments", 13, is_advanced=True),
    CalculatorColumn("non_refundable", "N", "Non-refundable", 14, is_advanced=True),
    CalculatorColumn("refundable", "O", "Refundable", 15, is_advanced=True),
    CalculatorColumn("url", "P", "URL", 16),
    CalculatorColumn("gross_price_per_unit", "Q", "Gross P per unit", 17),
    CalculatorColumn("units", "R", "Units", 18),
    CalculatorColumn("gross_price", "S", "Gross P", 19, is_formula=True),
    CalculatorColumn("supplier_commission", "T", "Supp Comm", 20),
    CalculatorColumn("net_price", "U", "Net P", 21, is_formula=True),
    CalculatorColumn("supplier_currency", "V", "Supp curr", 22),
    CalculatorColumn("supplier_x_rate", "W", "X-rate", 23, is_formula=True),
    CalculatorColumn("net_price_nok", "X", "Net P NOK", 24, is_formula=True),
    CalculatorColumn("sales_price_per_unit", "Y", "Sales P per unit", 25, is_formula=True),
    CalculatorColumn("price", "Z", "Price", 26, is_formula=True),
    CalculatorColumn("sales_currency", "AA", "Sales curr", 27),
    CalculatorColumn("sales_x_rate", "AB", "X-rate", 28, is_formula=True),
    CalculatorColumn("sales_price_nok_total", "AC", "Sales P NOK tot", 29, is_formula=True),
    CalculatorColumn("gp_nok", "AD", "GP NOK", 30, is_formula=True),
    CalculatorColumn("gp_percent", "AE", "GP %", 31, is_formula=True),
    CalculatorColumn("vat25", "AF", "VAT25", 32, is_advanced=True),
    CalculatorColumn("vat15", "AG", "VAT15", 33, is_advanced=True),
    CalculatorColumn("vat12", "AH", "VAT12", 34, is_advanced=True),
    CalculatorColumn("vat0_domestic", "AI", "VAT0-D", 35, is_advanced=True),
    CalculatorColumn("vat0_international", "AJ", "VAT0-I", 36, is_advanced=True),
)

COLUMN_BY_LETTER = {column.letter: column for column in COLUMN_SPECS}
COLUMN_BY_KEY = {column.key: column for column in COLUMN_SPECS}
HEADER_BY_LETTER = {column.letter: column.header for column in COLUMN_SPECS}
FORMULA_COLUMNS = tuple(column.letter for column in COLUMN_SPECS if column.is_formula)
ADVANCED_COLUMNS = tuple(column.letter for column in COLUMN_SPECS if column.is_advanced)
ADVANCED_COLUMN_RANGES = ("G:H", "I:I", "K:L", "M:M", "N:O", "AF:AJ")


def column_letters() -> tuple[str, ...]:
    """Return calculator workbook columns in template order."""

    return tuple(column.letter for column in COLUMN_SPECS)


def headers() -> tuple[str, ...]:
    """Return locked header labels in template order."""

    return tuple(column.header for column in COLUMN_SPECS)


def get_column_by_letter(letter: str) -> CalculatorColumn:
    """Return the column definition for an Excel column letter."""

    return COLUMN_BY_LETTER[letter.upper()]


def get_column_by_key(key: str) -> CalculatorColumn:
    """Return the column definition for a calculator field key."""

    return COLUMN_BY_KEY[key]
