from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


def test_travel_element_autocomplete_stays_open_during_a_typing_pause() -> None:
    library_row = {
        "library_id": "oslo-hotel",
        "label": "Oslo Hotel",
        "preview": "Hotel in Oslo",
        "travel_element": "Oslo Hotel",
        "supplier": "Supplier",
        "country": "Norway",
        "category": "Hotel",
        "type": "Hotel",
        "comments": "",
        "search_text": "oslo hotel norway",
        "url": "",
        "row_data": {
            "row_id": "",
            "type": "Hotel",
            "travel_element": "Oslo Hotel",
            "supplier": "Supplier",
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
        },
    }
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK"}],
            library_rows=[library_row],
            revision="autocomplete-no-sync",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(event.data.value);
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Osl")
        page.wait_for_timeout(900)

        assert page.locator(".suggestion-item").count() == 1
        assert page.evaluate("document.activeElement.dataset.key") == "travel_element"
        assert page.evaluate("activeCellEditing") is True
        assert page.evaluate("window.__calculatorComponentValues") == []

        page.locator(".suggestion-item").click()
        assert cell.text_content().strip() == "Oslo Hotel"
    finally:
        browser.close()
        manager.stop()

def test_fetched_suggestion_returns_focus_to_grid_navigation_mode() -> None:
    library_row = {
        "library_id": "hotel-1",
        "label": "Fetched Hotel",
        "preview": "Hotel in Oslo",
        "travel_element": "Fetched Hotel",
        "supplier": "Supplier",
        "country": "Norway",
        "category": "Hotel",
        "type": "Hotel",
        "comments": "",
        "search_text": "fetched hotel",
        "url": "",
        "row_data": {
            "row_id": "",
            "type": "Hotel",
            "travel_element": "Fetched Hotel",
            "supplier": "Supplier",
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
            "gross_price_per_unit": 100,
            "units": 1,
        },
    }
    manager, browser, page = _browser_page(
        _payload([{"row_id": "1", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK", "gross_price_per_unit": "", "units": ""}], library_rows=[library_row], revision="suggestion")
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Fetched")
        page.locator(".suggestion-item").wait_for(timeout=3000)
        page.locator(".suggestion-item").click()

        assert cell.text_content().strip() == "Fetched Hotel"
        assert page.evaluate("activeCellEditing") is False
        page.keyboard.press("ArrowRight")
        assert page.evaluate("document.activeElement.dataset.key") == "url"
    finally:
        browser.close()
        manager.stop()

def test_fetched_nok_product_defaults_sales_price_to_eur_conversion() -> None:
    library_row = {
        "library_id": "nok-activity",
        "label": "Oslo activity",
        "preview": "Priced in NOK",
        "travel_element": "Oslo activity",
        "supplier": "Supplier",
        "country": "Norway",
        "category": "Activity",
        "type": "Activity",
        "comments": "",
        "search_text": "oslo activity",
        "url": "",
        "row_data": {
            "row_id": "",
            "type": "Activity",
            "travel_element": "Oslo activity",
            "gross_price_per_unit": 1200,
            "units": 1,
            "supplier_currency": "NOK",
            "sales_price_per_unit": 0,
            "sales_currency": "NOK",
            "_sales_price_per_unit_touched": False,
        },
    }
    payload = _payload(
        [{"row_id": "1", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "EUR"}],
        library_rows=[library_row],
        revision="nok-to-eur-fetch",
    )
    payload["currency_rates"] = {"NOK": 1, "EUR": 12}
    manager, browser, page = _browser_page(payload)
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Oslo activity")
        page.locator(".suggestion-item").first.click()

        sales_cell = page.locator('td[data-row-index="0"][data-key="sales_price_per_unit"]')
        assert sales_cell.text_content().strip() == "100.00"
        assert page.evaluate("calculatorState.rows[0].sales_currency") == "EUR"
        assert page.evaluate("calculatorState.rows[0]._sales_price_per_unit_touched") is False
        assert page.evaluate("calculatorState.rows[0].sales_price_nok_total") == 1200
    finally:
        browser.close()
        manager.stop()


def test_fetched_product_keeps_workbook_provenance_in_browser_state() -> None:
    library_row = {
        "library_id": "activity-row-19",
        "source_workbook": "library.xlsx",
        "source_sheet": "Activities",
        "source_row": 19,
        "label": "Northern Lights Hunt",
        "preview": "Activity in Rovaniemi",
        "travel_element": "Northern Lights Hunt",
        "supplier": "Supplier",
        "country": "Finland",
        "category": "Activity",
        "type": "Activity",
        "comments": "",
        "url": "https://supplier.invalid/19",
        "row_data": {
            "type": "Activity",
            "travel_element": "Northern Lights Hunt",
            "supplier": "Supplier",
            "url": "https://supplier.invalid/19",
            "supplier_currency": "NOK",
            "sales_currency": "EUR",
        },
    }
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "EUR"}],
            library_rows=[library_row],
            revision="provenance-selection",
        )
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="travel_element"]')
        cell.click()
        page.keyboard.type("Northern Lights")
        page.locator(".suggestion-item").first.click()

        lineage = page.evaluate("""() => {
          const row = calculatorState.rows[0];
          return [row.library_id, row.source_workbook, row.source_sheet, row.source_row, row.url];
        }""")
        assert lineage == [
            "activity-row-19",
            "library.xlsx",
            "Activities",
            19,
            "https://supplier.invalid/19",
        ]
    finally:
        browser.close()
        manager.stop()
