"""Financial precision policy shared by calculator calculations and exports."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000001")
PERCENT_QUANTUM = Decimal("0.000001")


def decimal_value(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    """Return a finite Decimal without binary-float artefacts."""

    if value in (None, ""):
        return default
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default
    return result if result.is_finite() else default


def round_money(value: Any) -> Decimal:
    """Round money exactly like Excel ROUND(..., 2): half away from zero."""

    return decimal_value(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def round_rate(value: Any) -> Decimal:
    """Round exchange rates to six decimal places."""

    return decimal_value(value).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


def round_percent(value: Any) -> Decimal:
    """Round stored decimal percentages to six decimal places."""

    return decimal_value(value).quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)


def as_float(value: Decimal) -> float:
    """Convert a canonical Decimal result at the public/UI boundary."""

    return float(value)
