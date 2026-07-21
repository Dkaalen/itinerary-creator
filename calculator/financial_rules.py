"""Versioned financial precision and margin rules shared across calculator boundaries."""

from __future__ import annotations

from decimal import Decimal
import re
from typing import Any

from calculator.numeric_input import parse_decimal_input_strict
from calculator.precision import as_float, round_money, round_percent, round_rate

FINANCIAL_RULES_VERSION = "financial-v1"
MONEY_DIGITS = 2
RATE_DIGITS = 6
PERCENT_DIGITS = 6
COMMISSION_UI_SCALE = 100

FORMULA_RESULT_KIND_BY_FIELD: dict[str, str] = {
    "gross_price": "money",
    "net_price": "money",
    "supplier_x_rate": "rate",
    "net_price_nok": "money",
    "price": "money",
    "sales_x_rate": "rate",
    "sales_price_nok_total": "money",
    "gp_nok": "money",
    "gp_percent": "percent",
}
EXPORT_PRECISION_KIND_BY_FIELD: dict[str, str] = {
    **FORMULA_RESULT_KIND_BY_FIELD,
    "supplier_commission": "percent",
}
SALES_PRICE_DERIVED_OVERRIDE_FIELDS: tuple[str, ...] = (
    "price_override",
    "sales_price_nok_total_override",
    "gp_nok_override",
    "gp_percent_override",
)


def financial_rules_payload() -> dict[str, Any]:
    """Return the JSON-safe contract consumed by the browser calculator."""

    return {
        "version": FINANCIAL_RULES_VERSION,
        "precision_digits": {
            "money": MONEY_DIGITS,
            "rate": RATE_DIGITS,
            "percent": PERCENT_DIGITS,
        },
        "commission_ui_scale": COMMISSION_UI_SCALE,
        "formula_result_kind_by_field": dict(FORMULA_RESULT_KIND_BY_FIELD),
        "margin_basis": "net_price_nok",
        "sales_price_derived_override_fields": list(SALES_PRICE_DERIVED_OVERRIDE_FIELDS),
    }


def round_formula_result(field_name: str, value: Any) -> Decimal:
    """Round one calculated formula field according to the canonical policy."""

    return round_for_kind(FORMULA_RESULT_KIND_BY_FIELD.get(field_name, "money"), value)


def round_for_kind(kind: str, value: Any) -> Decimal:
    """Round a value using the named financial precision."""

    if kind == "rate":
        return round_rate(value)
    if kind == "percent":
        return round_percent(value)
    return round_money(value)


def canonical_export_value(field_name: str, value: Any) -> Any:
    """Return an Excel value whose calculation precision matches Python/browser rules."""

    kind = EXPORT_PRECISION_KIND_BY_FIELD.get(field_name)
    if kind is None or value in (None, ""):
        return value
    if isinstance(value, str) and value.strip().startswith("="):
        expression = value.strip()[1:].strip()
        digits = precision_digits(kind)
        return f"=ROUND(({expression}),{digits})"
    parsed = parse_decimal_input_strict(value, allow_blank=False)
    assert parsed is not None
    return as_float(round_for_kind(kind, parsed))


def unwrap_canonical_export_formula(field_name: str, formula: str) -> str:
    """Remove the app's Excel-only precision wrapper from a re-imported formula."""

    kind = EXPORT_PRECISION_KIND_BY_FIELD.get(field_name)
    if kind is None:
        return formula
    digits = precision_digits(kind)
    match = re.fullmatch(
        rf"\s*=\s*ROUND\s*\(\s*\((.*)\)\s*,\s*{digits}\s*\)\s*",
        str(formula or ""),
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return formula
    return f"={match.group(1).strip()}"


def precision_digits(kind: str) -> int:
    if kind == "rate":
        return RATE_DIGITS
    if kind == "percent":
        return PERCENT_DIGITS
    return MONEY_DIGITS


__all__ = [
    "COMMISSION_UI_SCALE",
    "EXPORT_PRECISION_KIND_BY_FIELD",
    "FINANCIAL_RULES_VERSION",
    "FORMULA_RESULT_KIND_BY_FIELD",
    "MONEY_DIGITS",
    "PERCENT_DIGITS",
    "RATE_DIGITS",
    "SALES_PRICE_DERIVED_OVERRIDE_FIELDS",
    "canonical_export_value",
    "financial_rules_payload",
    "precision_digits",
    "round_for_kind",
    "round_formula_result",
    "unwrap_canonical_export_formula",
]
