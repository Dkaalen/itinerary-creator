from __future__ import annotations

from datetime import datetime, timezone

from calculator.defaults import DEFAULT_CALCULATOR_CURRENCY
from calculator.library_editor import (
    display_label_for_local_library_row,
    mark_local_library_row_deleted,
    new_local_library_row,
    update_local_library_row,
)
from calculator.library_model import LINE_RECORD_TYPE, LocalLibraryRow

_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_new_local_library_row_is_active_fetchable_line_with_default_currency() -> None:
    row = new_local_library_row(now=_NOW, library_id="manual_test")

    assert row.library_id == "manual_test"
    assert row.record_type == LINE_RECORD_TYPE
    assert row.is_deleted is False
    assert row.is_fetchable is True
    assert row.supplier_currency == DEFAULT_CALCULATOR_CURRENCY
    assert row.sales_currency == DEFAULT_CALCULATOR_CURRENCY
    assert row.created_at == "2026-01-02T03:04:05+00:00"
    assert row.updated_at == "2026-01-02T03:04:05+00:00"


def test_update_local_library_row_converts_editor_values() -> None:
    row = new_local_library_row(now=_NOW, library_id="manual_test")

    updated = update_local_library_row(
        row,
        {
            "country": " no ",
            "category": "Activities",
            "type": "Activity",
            "supplier": "Guide",
            "travel_element": "Fjord walk",
            "gross_price_per_unit": "10,5",
            "units": "2",
            "supplier_commission": "20",
            "supplier_currency": " eur ",
            "sales_price_per_unit": "15",
            "sales_currency": " usd ",
            "manual_booking": "TRUE",
            "is_fetchable": "x",
        },
        now=_NOW,
    )

    assert updated.country == "no"
    assert updated.travel_element == "Fjord walk"
    assert updated.gross_price_per_unit == 10.5
    assert updated.units == 2
    assert updated.supplier_commission == 0.2
    assert updated.supplier_currency == "EUR"
    assert updated.sales_currency == "USD"
    assert updated.manual_booking is True
    assert updated.is_fetchable is True
    assert updated.is_deleted is False


def test_mark_local_library_row_deleted_soft_deletes_and_hides_from_fetch() -> None:
    row = LocalLibraryRow(library_id="row_1", is_fetchable=True)

    deleted = mark_local_library_row_deleted(row, now=_NOW)

    assert deleted.is_deleted is True
    assert deleted.is_fetchable is False
    assert deleted.updated_at == "2026-01-02T03:04:05+00:00"


def test_display_label_uses_country_category_and_element() -> None:
    row = LocalLibraryRow(country="NO", category="Activity", travel_element="Fjord cruise")

    assert display_label_for_local_library_row(row) == "NO · Activity · Fjord cruise"
