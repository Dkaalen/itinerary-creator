"""Data contracts for calculator rows."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from calculator.defaults import DEFAULT_CALCULATOR_CURRENCY

BASIC_FIELD_KEYS = (
    "row_id",
    "day",
    "type",
    "from_date",
    "to_date",
    "travel_element",
    "url",
    "gross_price_per_unit",
    "units",
    "supplier_commission",
    "supplier_currency",
    "sales_price_per_unit",
    "sales_currency",
)
ADVANCED_FIELD_KEYS = (
    "from_time",
    "to_time",
    "supplier",
    "manual_booking",
    "status",
    "comments",
    "non_refundable",
    "refundable",
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
)
VAT_FIELD_KEYS = (
    "vat25",
    "vat15",
    "vat12",
    "vat0_domestic",
    "vat0_international",
)
FORMULA_FIELD_KEYS = (
    "gross_price",
    "net_price",
    "supplier_x_rate",
    "net_price_nok",
    "price",
    "sales_x_rate",
    "sales_price_nok_total",
    "gp_nok",
    "gp_percent",
)
FORMULA_OVERRIDE_FIELD_BY_KEY = {
    "gross_price": "gross_price_override",
    "net_price": "net_price_override",
    "supplier_x_rate": "supplier_x_rate_override",
    "net_price_nok": "net_price_nok_override",
    "price": "price_override",
    "sales_x_rate": "sales_x_rate_override",
    "sales_price_nok_total": "sales_price_nok_total_override",
    "gp_nok": "gp_nok_override",
    "gp_percent": "gp_percent_override",
}
FORMULA_OVERRIDE_FIELDS = tuple(FORMULA_OVERRIDE_FIELD_BY_KEY.values())


@dataclass(frozen=True)
class CalculatorRow:
    """One editable calculator line before formulas are applied."""

    row_id: str = ""
    day: str = ""
    type: str = ""
    from_date: str = ""
    to_date: str = ""
    from_time: str = ""
    to_time: str = ""
    supplier: str = ""
    travel_element: str = ""
    manual_booking: bool = False
    status: str = ""
    comments: str = ""
    non_refundable: bool = False
    refundable: bool = False
    url: str = ""
    gross_price_per_unit: float = 0.0
    units: float = 0.0
    supplier_commission: float = 0.0
    supplier_currency: str = DEFAULT_CALCULATOR_CURRENCY
    sales_price_per_unit: float | None = None
    sales_currency: str = DEFAULT_CALCULATOR_CURRENCY
    vat25: float = 0.0
    vat15: float = 0.0
    vat12: float = 0.0
    vat0_domestic: float = 0.0
    vat0_international: float = 0.0
    gross_price_override: float | None = None
    net_price_override: float | None = None
    supplier_x_rate_override: float | None = None
    net_price_nok_override: float | None = None
    price_override: float | None = None
    sales_x_rate_override: float | None = None
    sales_price_nok_total_override: float | None = None
    gp_nok_override: float | None = None
    gp_percent_override: float | None = None

    def with_changes(self, **changes: Any) -> "CalculatorRow":
        """Return a copy of this row with selected fields changed."""

        return replace(self, **changes)


@dataclass(frozen=True)
class CalculatedRow:
    """One calculator line after formula values are calculated."""

    source: CalculatorRow
    gross_price: float
    net_price: float
    supplier_x_rate: float
    net_price_nok: float
    calculated_sales_price_per_unit: float
    price: float
    sales_x_rate: float
    sales_price_nok_total: float
    gp_nok: float
    gp_percent: float

    @property
    def row_id(self) -> str:
        """Return the source row identifier."""

        return self.source.row_id
