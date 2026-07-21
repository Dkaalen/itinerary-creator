"""Validation for calculator state before save-sensitive actions and export."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Mapping

from calculator.calculator_state import CalculatorState
from calculator.cell_formula_engine import CalculatorCellFormulaEvaluator, CellFormulaError
from calculator.currency_rates import normalize_currency_rates, normalized_currency_code
from calculator.row_model import CalculatorRow
from calculator.numeric_input import parse_decimal_input_strict


@dataclass(frozen=True)
class CalculatorValidationIssue:
    """One actionable calculator validation problem."""

    code: str
    message: str
    row_id: str = ""
    field: str = ""


class CalculatorValidationError(ValueError):
    """Raised when an export or other strict action receives invalid state."""

    def __init__(self, issues: tuple[CalculatorValidationIssue, ...]):
        self.issues = issues
        summary = "; ".join(issue.message for issue in issues[:5])
        if len(issues) > 5:
            summary += f"; and {len(issues) - 5} more issue(s)"
        super().__init__(summary or "Calculator state is invalid.")


class CalculatorValidationScope(str, Enum):
    """Validation boundary for one Calculator workflow action."""

    DRAFT_SAFE = "draft_safe"
    PERSISTENCE = "persistence"
    EXPORT = "export"
    GENERATION = "generation"
    IMPORT = "import"


_NUMERIC_CELL_BY_FIELD = {
    "gross_price_per_unit": "Q",
    "units": "R",
    "supplier_commission": "T",
    "sales_price_per_unit": "Y",
    "vat25": "AF",
    "vat15": "AG",
    "vat12": "AH",
    "vat0_domestic": "AI",
    "vat0_international": "AJ",
    "gross_price_override": "S",
    "net_price_override": "U",
    "supplier_x_rate_override": "W",
    "net_price_nok_override": "X",
    "price_override": "Z",
    "sales_x_rate_override": "AB",
    "sales_price_nok_total_override": "AC",
    "gp_nok_override": "AD",
    "gp_percent_override": "AE",
}
_PERSISTED_NUMERIC_FIELDS = tuple(_NUMERIC_CELL_BY_FIELD)
_GENERATION_CONTENT_FIELDS = (
    "day",
    "type",
    "from_date",
    "to_date",
    "from_time",
    "to_time",
    "supplier",
    "travel_element",
    "comments",
    "url",
)
_NON_GENERATING_TYPES = {"", "total", "subtotal", "sub total"}


def validate_calculator_state(
    state: CalculatorState,
    currency_rates: Mapping[str, float] | None = None,
    *,
    scope: CalculatorValidationScope | str = CalculatorValidationScope.EXPORT,
) -> tuple[CalculatorValidationIssue, ...]:
    """Return deterministic issues for the requested workflow boundary."""

    resolved_scope = CalculatorValidationScope(scope)
    if resolved_scope is CalculatorValidationScope.DRAFT_SAFE:
        return ()
    if resolved_scope is CalculatorValidationScope.GENERATION:
        return _validate_generation_state(state)
    if resolved_scope in {CalculatorValidationScope.PERSISTENCE, CalculatorValidationScope.IMPORT}:
        return _validate_persistable_state(state, currency_rates)

    rates = normalize_currency_rates(currency_rates)
    issues: list[CalculatorValidationIssue] = []
    seen_ids: set[str] = set()
    evaluator = CalculatorCellFormulaEvaluator(state.rows, rates)

    for index, row in enumerate(state.rows, start=1):
        row_id = str(row.row_id or index)
        if row_id in seen_ids:
            issues.append(
                CalculatorValidationIssue(
                    code="duplicate_row_id",
                    row_id=row_id,
                    field="row_id",
                    message=f"Row ID {row_id} is duplicated.",
                )
            )
        seen_ids.add(row_id)
        issues.extend(_validate_row(row, row_id, rates, evaluator, index + 6))
    return tuple(issues)


def ensure_valid_calculator_state(
    state: CalculatorState,
    currency_rates: Mapping[str, float] | None = None,
    *,
    scope: CalculatorValidationScope | str = CalculatorValidationScope.EXPORT,
) -> None:
    """Raise CalculatorValidationError when the requested action is unsafe."""

    issues = validate_calculator_state(state, currency_rates, scope=scope)
    if issues:
        raise CalculatorValidationError(issues)


def _validate_persistable_state(
    state: CalculatorState,
    currency_rates: Mapping[str, float] | None,
) -> tuple[CalculatorValidationIssue, ...]:
    issues: list[CalculatorValidationIssue] = []
    seen_ids: set[str] = set()
    evaluator = CalculatorCellFormulaEvaluator(state.rows, normalize_currency_rates(currency_rates))
    pax = state.number_of_pax
    if pax not in (None, ""):
        valid_pax = _positive_whole_number_or_none(pax) is not None
        if not valid_pax:
            issues.append(
                CalculatorValidationIssue(
                    code="invalid_pax",
                    field="number_of_pax",
                    message="No. of pax must be a positive whole number or blank before saving.",
                )
            )

    for index, row in enumerate(state.rows, start=1):
        row_id = str(row.row_id or index)
        if row_id in seen_ids:
            issues.append(
                CalculatorValidationIssue(
                    code="duplicate_row_id",
                    row_id=row_id,
                    field="row_id",
                    message=f"Row ID {row_id} is duplicated.",
                )
            )
        seen_ids.add(row_id)
        for field in _PERSISTED_NUMERIC_FIELDS:
            value = getattr(row, field)
            if value in (None, ""):
                continue
            if isinstance(value, str):
                column = _NUMERIC_CELL_BY_FIELD[field]
                if column:
                    try:
                        evaluator.evaluate_cell(f"{column}{index + 6}")
                    except (CellFormulaError, ValueError) as error:
                        code = error.code if isinstance(error, CellFormulaError) else "invalid_number"
                        issues.append(
                            CalculatorValidationIssue(
                                code=code,
                                row_id=row_id,
                                field=field,
                                message=f"Row {row_id}: {field.replace('_', ' ')} has an invalid formula ({error}).",
                            )
                        )
                continue
            if isinstance(value, bool):
                valid = False
            else:
                try:
                    valid = isfinite(float(value))
                except (TypeError, ValueError):
                    valid = False
            if not valid:
                issues.append(
                    CalculatorValidationIssue(
                        code="non_persistable_number",
                        row_id=row_id,
                        field=field,
                        message=f"Row {row_id}: {field.replace('_', ' ')} must be finite or contain a formula before saving.",
                    )
                )
    return tuple(issues)



def _positive_whole_number_or_none(value: object) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number <= 0 or not number.is_integer():
        return None
    return int(number)


def _validate_generation_state(state: CalculatorState) -> tuple[CalculatorValidationIssue, ...]:
    issues: list[CalculatorValidationIssue] = []
    complete_rows = 0
    for index, row in enumerate(state.rows, start=1):
        row_id = str(row.row_id or index)
        row_type = _clean_text(row.type)
        travel_element = _clean_text(row.travel_element)
        has_generation_content = any(_clean_text(getattr(row, field)) for field in _GENERATION_CONTENT_FIELDS)
        if not has_generation_content:
            continue
        if row_type.casefold() in _NON_GENERATING_TYPES:
            if not row_type:
                issues.append(
                    CalculatorValidationIssue(
                        code="missing_generation_type",
                        row_id=row_id,
                        field="type",
                        message=f"Row {row_id}: Type is required before generating an itinerary.",
                    )
                )
            continue
        if not travel_element:
            issues.append(
                CalculatorValidationIssue(
                    code="missing_generation_travel_element",
                    row_id=row_id,
                    field="travel_element",
                    message=f"Row {row_id}: Travel element is required before generating an itinerary.",
                )
            )
            continue
        complete_rows += 1

    if complete_rows == 0 and not issues:
        issues.append(
            CalculatorValidationIssue(
                code="no_generatable_rows",
                field="travel_element",
                message="Add at least one calculator row with both Type and Travel element before generating an itinerary.",
            )
        )
    return tuple(issues)


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _validate_row(
    row: CalculatorRow,
    row_id: str,
    rates: Mapping[str, float],
    evaluator: CalculatorCellFormulaEvaluator,
    row_number: int,
) -> list[CalculatorValidationIssue]:
    issues: list[CalculatorValidationIssue] = []
    for field, column in _NUMERIC_CELL_BY_FIELD.items():
        value = getattr(row, field)
        if value is None or value == "":
            continue
        try:
            evaluator.evaluate_cell(f"{column}{row_number}")
        except (CellFormulaError, ValueError) as error:
            code = error.code if isinstance(error, CellFormulaError) else "invalid_number"
            issues.append(
                CalculatorValidationIssue(
                    code=code,
                    row_id=row_id,
                    field=field,
                    message=f"Row {row_id}: {field.replace('_', ' ')} has an invalid formula ({error}).",
                )
            )

    try:
        commission = float(evaluator.evaluate_cell(f"T{row_number}"))
    except (CellFormulaError, ValueError):
        commission = 0.0
    if commission < 0 or commission > 1:
        issues.append(
            CalculatorValidationIssue(
                code="invalid_commission",
                row_id=row_id,
                field="supplier_commission",
                message=f"Row {row_id}: supplier commission must be between 0% and 100%.",
            )
        )

    for field, override_field in (
        ("supplier_currency", "supplier_x_rate_override"),
        ("sales_currency", "sales_x_rate_override"),
    ):
        code = normalized_currency_code(getattr(row, field), default="")
        override = getattr(row, override_field)
        if override is not None:
            try:
                rate_column = "W" if field == "supplier_currency" else "AB"
                parsed_override = evaluator.evaluate_cell(f"{rate_column}{row_number}")
                valid_override = parsed_override > 0
            except (CellFormulaError, ValueError):
                valid_override = False
            if not valid_override:
                issues.append(
                    CalculatorValidationIssue(
                        code="invalid_exchange_rate_override",
                        row_id=row_id,
                        field=override_field,
                        message=f"Row {row_id}: manual exchange rate must be greater than zero.",
                    )
                )
            continue
        rate = rates.get(code)
        if not code or rate is None or not isfinite(float(rate)) or float(rate) <= 0:
            issues.append(
                CalculatorValidationIssue(
                    code="missing_exchange_rate",
                    row_id=row_id,
                    field=field,
                    message=f"Row {row_id}: no positive NOK exchange rate exists for {code or 'the selected currency'}.",
                )
            )
    return issues
