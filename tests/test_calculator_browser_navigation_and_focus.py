from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


def test_first_click_on_prefilled_cell_enables_immediate_arrow_navigation() -> None:
    manager, browser, page = _browser_page(
        _payload([{"row_id": "1", "travel_element": "Fetched hotel", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1}])
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.press("ArrowRight")

        assert page.evaluate("document.activeElement.dataset.key") == "url"
        assert page.evaluate("activeCellEditing") is False
    finally:
        browser.close()
        manager.stop()

def test_selecting_prefilled_library_cell_does_not_open_suggestions_or_steal_arrows() -> None:
    library_row = {
        "library_id": "hotel-prefilled",
        "label": "Fetched Hotel",
        "preview": "Hotel in Oslo",
        "travel_element": "Fetched Hotel",
        "search_text": "fetched hotel",
        "row_data": {"travel_element": "Fetched Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"},
    }
    rows = [{"row_id": "1", "travel_element": "Fetched Hotel", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": 100, "units": 1}]
    manager, browser, page = _browser_page(_payload(rows, library_rows=[library_row], revision="prefilled-focus"))
    try:
        page.locator('td[data-row-index="0"][data-key="travel_element"]').click()
        page.wait_for_timeout(250)
        assert page.locator('.suggestion-panel').count() == 0
        page.keyboard.press("ArrowRight")
        assert page.evaluate("document.activeElement.dataset.key") == "url"
    finally:
        browser.close()
        manager.stop()
