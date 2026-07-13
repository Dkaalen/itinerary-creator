"""Validation for calculator state before save-sensitive actions and export."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from calculator.calculator_state import CalculatorState
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


def validate_calculator_state(
    state: CalculatorState,
    currency_rates: Mapping[str, float] | None = None,
) -> tuple[CalculatorValidationIssue, ...]:
    """Return deterministic validation issues for the current calculator state."""

    rates = normalize_currency_rates(currency_rates)
    issues: list[CalculatorValidationIssue] = []
    seen_ids: set[str] = set()

    if state.number_of_pax is not None and state.number_of_pax <= 0:
        issues.append(
            CalculatorValidationIssue(
                code="invalid_pax",
                field="number_of_pax",
                message="No. of pax must be greater than zero or left blank.",
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
        issues.extend(_validate_row(row, row_id, rates))
    return tuple(issues)


def ensure_valid_calculator_state(
    state: CalculatorState,
    currency_rates: Mapping[str, float] | None = None,
) -> None:
    """Raise CalculatorValidationError when the state is unsafe to export."""

    issues = validate_calculator_state(state, currency_rates)
    if issues:
        raise CalculatorValidationError(issues)


def _validate_row(
    row: CalculatorRow,
    row_id: str,
    rates: Mapping[str, float],
) -> list[CalculatorValidationIssue]:
    issues: list[CalculatorValidationIssue] = []
    numeric_fields = (
        "gross_price_per_unit",
        "units",
        "supplier_commission",
        "sales_price_per_unit",
        "vat25",
        "vat15",
        "vat12",
        "vat0_domestic",
        "vat0_international",
        "gross_price_override",
        "net_price_override",
        "supplier_x_rate_override",
        "net_price_nok_override",
        "price_override",
        "sales_x_rate_override",
        "sales_price_nok_total_override",
        "gp_nok_override",
        "gp_percent_override",
    )
    for field in numeric_fields:
        value = getattr(row, field)
        if value is None:
            continue
        try:
            parse_decimal_input_strict(value)
            finite = True
        except ValueError:
            finite = False
        if not finite:
            issues.append(
                CalculatorValidationIssue(
                    code="invalid_number",
                    row_id=row_id,
                    field=field,
                    message=f"Row {row_id}: {field.replace('_', ' ')} is not a valid finite number.",
                )
            )

    try:
        commission_value = parse_decimal_input_strict(row.supplier_commission, allow_blank=False)
        commission = float(commission_value) if commission_value is not None else 0.0
    except ValueError:
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
                parsed_override = parse_decimal_input_strict(override, allow_blank=False)
                valid_override = parsed_override is not None and parsed_override > 0
            except ValueError:
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
