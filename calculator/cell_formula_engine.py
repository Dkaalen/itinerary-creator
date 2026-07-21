"""Exact A1-style formula evaluation for calculator numeric cells."""

from __future__ import annotations

from decimal import Decimal
import re
from typing import Mapping, Sequence

from calculator.currency_rates import normalize_currency_rates, normalized_currency_code
from calculator.financial_rules import round_formula_result
from calculator.numeric_input import parse_decimal_input_strict
from calculator.precision import round_money, round_percent, round_rate
from calculator.row_model import FORMULA_OVERRIDE_FIELD_BY_KEY, CalculatorRow, CalculatedRow

_DATA_START_ROW = 7
_DATA_END_ROW = 99
_CELL_REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])\$?([A-Z]{1,2})\$?(\d+)(?![A-Za-z0-9_])")
_PERCENT_RE = re.compile(r"(?P<number>(?:\d+(?:\.\d*)?|\.\d+))\s*%")
_ALLOWED_EXPRESSION_RE = re.compile(r"^[0-9+\-*/().\s]+$")
_NUMERIC_INPUT_BY_COLUMN = {
    "Q": "gross_price_per_unit",
    "R": "units",
    "T": "supplier_commission",
    "AF": "vat25",
    "AG": "vat15",
    "AH": "vat12",
    "AI": "vat0_domestic",
    "AJ": "vat0_international",
}
_FORMULA_COLUMN_BY_FIELD = {
    "S": "gross_price",
    "U": "net_price",
    "W": "supplier_x_rate",
    "X": "net_price_nok",
    "Z": "price",
    "AB": "sales_x_rate",
    "AC": "sales_price_nok_total",
    "AD": "gp_nok",
    "AE": "gp_percent",
}


class CellFormulaError(ValueError):
    """Raised for invalid, circular, or unsupported calculator formulas."""

    def __init__(self, code: str, message: str, *, cell: str = ""):
        self.code = code
        self.cell = cell
        super().__init__(message)


class CalculatorCellFormulaEvaluator:
    """Resolve calculator A1 references with exact Decimal arithmetic."""

    def __init__(
        self,
        rows: Sequence[CalculatorRow],
        currency_rates: Mapping[str, float] | None = None,
    ) -> None:
        self.rows = tuple(rows)
        self.rates = normalize_currency_rates(currency_rates)
        self._cache: dict[str, Decimal] = {}
        self._visiting: list[str] = []

    def evaluate_expression(self, value: object, *, current_cell: str = "") -> Decimal:
        """Evaluate arithmetic and A1 references, returning an exact Decimal."""

        if value is None or value == "":
            return Decimal("0")
        if not isinstance(value, str):
            parsed = parse_decimal_input_strict(value, allow_blank=False)
            assert parsed is not None
            return parsed

        text = value.strip().replace(",", ".")
        if text.startswith("="):
            text = text[1:].strip()
        if not text:
            return Decimal("0")

        def replace_reference(match: re.Match[str]) -> str:
            ref = f"{match.group(1)}{int(match.group(2))}"
            return f"({self.evaluate_cell(ref)})"

        substituted = _CELL_REFERENCE_RE.sub(replace_reference, text)
        substituted = _PERCENT_RE.sub(r"(\g<number>/100)", substituted)
        if not _ALLOWED_EXPRESSION_RE.fullmatch(substituted):
            raise CellFormulaError(
                "#VALUE!",
                f"{current_cell or 'Formula'} contains unsupported text or functions.",
                cell=current_cell,
            )
        try:
            parsed = parse_decimal_input_strict(substituted, allow_blank=False)
        except ValueError as error:
            message = str(error)
            code = "#DIV/0!" if "/0" in substituted.replace(" ", "") else "#VALUE!"
            raise CellFormulaError(code, f"{current_cell or 'Formula'} is invalid: {message}", cell=current_cell) from error
        assert parsed is not None
        return parsed

    def evaluate_cell(self, reference: str) -> Decimal:
        """Evaluate one calculator cell, following dependencies recursively."""

        normalized = reference.replace("$", "").upper()
        if normalized in self._cache:
            return self._cache[normalized]
        match = re.fullmatch(r"([A-Z]{1,2})(\d+)", normalized)
        if not match:
            raise CellFormulaError("#REF!", f"Invalid cell reference {reference!r}.", cell=normalized)
        column, row_text = match.groups()
        row_number = int(row_text)
        if row_number < _DATA_START_ROW or row_number > _DATA_END_ROW:
            raise CellFormulaError(
                "#REF!",
                f"Cell {normalized} is outside calculator rows {_DATA_START_ROW}–{_DATA_END_ROW}.",
                cell=normalized,
            )
        row_index = row_number - _DATA_START_ROW
        if row_index >= len(self.rows):
            return Decimal("0")
        if normalized in self._visiting:
            cycle = " → ".join((*self._visiting[self._visiting.index(normalized) :], normalized))
            raise CellFormulaError("#CIRC!", f"Circular reference: {cycle}.", cell=normalized)

        self._visiting.append(normalized)
        try:
            result = self._evaluate_cell_value(column, row_number, self.rows[row_index])
        finally:
            self._visiting.pop()
        self._cache[normalized] = result
        return result

    def calculated_rows(self) -> tuple[CalculatedRow, ...]:
        """Return canonical calculated rows using the shared dependency graph."""

        calculated: list[CalculatedRow] = []
        for index, row in enumerate(self.rows):
            number = _DATA_START_ROW + index
            calculated.append(
                CalculatedRow(
                    source=row,
                    gross_price=float(self.evaluate_cell(f"S{number}")),
                    net_price=float(self.evaluate_cell(f"U{number}")),
                    supplier_x_rate=float(self.evaluate_cell(f"W{number}")),
                    net_price_nok=float(self.evaluate_cell(f"X{number}")),
                    calculated_sales_price_per_unit=float(self.evaluate_cell(f"Y{number}")),
                    price=float(self.evaluate_cell(f"Z{number}")),
                    sales_x_rate=float(self.evaluate_cell(f"AB{number}")),
                    sales_price_nok_total=float(self.evaluate_cell(f"AC{number}")),
                    gp_nok=float(self.evaluate_cell(f"AD{number}")),
                    gp_percent=float(self.evaluate_cell(f"AE{number}")),
                )
            )
        return tuple(calculated)

    def _evaluate_cell_value(self, column: str, row_number: int, row: CalculatorRow) -> Decimal:
        ref = f"{column}{row_number}"
        input_field = _NUMERIC_INPUT_BY_COLUMN.get(column)
        if input_field:
            return self.evaluate_expression(getattr(row, input_field), current_cell=ref)
        if column == "Y":
            raw = row.sales_price_per_unit
            gross = self.evaluate_cell(f"Q{row_number}")
            sales_rate = self.evaluate_cell(f"AB{row_number}")
            default_value = (
                Decimal("0")
                if sales_rate == 0
                else gross * self.evaluate_cell(f"W{row_number}") / sales_rate
            )
            if raw is None or raw == "":
                return default_value
            value = self.evaluate_expression(raw, current_cell=ref)
            return default_value if value == 0 and gross > 0 else value

        formula_field = _FORMULA_COLUMN_BY_FIELD.get(column)
        if formula_field:
            override_field = FORMULA_OVERRIDE_FIELD_BY_KEY[formula_field]
            override = getattr(row, override_field)
            if override is not None and override != "":
                value = self.evaluate_expression(override, current_cell=ref)
                return round_formula_result(formula_field, value)

        if column == "S":
            return round_money(self.evaluate_cell(f"Q{row_number}") * self.evaluate_cell(f"R{row_number}"))
        if column == "U":
            commission = round_percent(self.evaluate_cell(f"T{row_number}"))
            return round_money(self.evaluate_cell(f"S{row_number}") * (Decimal("1") - commission))
        if column == "W":
            return self._currency_rate(row.supplier_currency)
        if column == "X":
            return round_money(self.evaluate_cell(f"U{row_number}") * self.evaluate_cell(f"W{row_number}"))
        if column == "Z":
            return round_money(self.evaluate_cell(f"Y{row_number}") * self.evaluate_cell(f"R{row_number}"))
        if column == "AB":
            return self._currency_rate(row.sales_currency)
        if column == "AC":
            return round_money(
                self.evaluate_cell(f"Z{row_number}") * self.evaluate_cell(f"AB{row_number}")
            )
        if column == "AD":
            return round_money(self.evaluate_cell(f"AC{row_number}") - self.evaluate_cell(f"X{row_number}"))
        if column == "AE":
            sales = self.evaluate_cell(f"AC{row_number}")
            return Decimal("0") if sales == 0 else self.evaluate_cell(f"AD{row_number}") / sales
        raise CellFormulaError(
            "#VALUE!",
            f"Cell {ref} is text or unsupported and cannot be used in a numeric formula.",
            cell=ref,
        )

    def _currency_rate(self, code: object) -> Decimal:
        normalized = normalized_currency_code(code, default="")
        return round_rate(self.rates.get(normalized, 0.0))

    def sales_price_per_unit_for_margin(self, row_number: int, margin: object) -> Decimal:
        """Return the unit sales price required for a target GP margin."""

        margin_value = parse_decimal_input_strict(margin, allow_blank=False)
        assert margin_value is not None
        if margin_value <= 0 or margin_value >= 1:
            return Decimal("0")
        units = self.evaluate_cell(f"R{row_number}")
        sales_rate = self.evaluate_cell(f"AB{row_number}")
        net_price_nok = self.evaluate_cell(f"X{row_number}")
        denominator = units * sales_rate * (Decimal("1") - margin_value)
        if denominator <= 0 or net_price_nok <= 0:
            return Decimal("0")
        return net_price_nok / denominator


def formula_references(value: object) -> tuple[str, ...]:
    """Return normalized A1 references used by a formula string."""

    if not isinstance(value, str):
        return ()
    return tuple(f"{match.group(1)}{int(match.group(2))}" for match in _CELL_REFERENCE_RE.finditer(value.upper()))
