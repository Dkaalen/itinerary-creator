from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


def test_cross_row_formula_dependents_refresh_immediately_after_edit() -> None:
    rows = [
        {"row_id": "1", "gross_price_per_unit": 100, "units": 2, "supplier_currency": "NOK", "sales_currency": "NOK"},
        {"row_id": "2", "gross_price_per_unit": "=S7/4", "units": 1, "supplier_currency": "NOK", "sales_currency": "NOK"},
    ]
    manager, browser, page = _browser_page(_payload(rows, revision="a1-dependent-refresh"))
    try:
        dependent = page.locator('td[data-row-index="1"][data-key="gross_price"]')
        assert dependent.text_content().strip() == "50.00"

        source = page.locator('td[data-row-index="0"][data-key="gross_price_per_unit"]')
        source.click()
        source.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("200")
        page.keyboard.press("Tab")

        assert dependent.text_content().strip() == "100.00"
    finally:
        browser.close()
        manager.stop()

def test_sales_price_expression_is_precise_internally_and_shows_two_decimals() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "1",
                "gross_price_per_unit": 600,
                "units": 1,
                "supplier_commission": 0,
                "supplier_currency": "NOK",
                "sales_price_per_unit": 600,
                "sales_currency": "NOK",
            }],
            revision="sales-price-expression",
        )
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="sales_price_per_unit"]')
        cell.click()
        page.keyboard.type("600/0.7")
        page.keyboard.press("Tab")

        assert cell.text_content().strip() == "857.14"
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600 / 0.7)
        assert page.evaluate("calculatorState.rows[0].price") == pytest.approx(857.14)
    finally:
        browser.close()
        manager.stop()

def test_sales_margin_shortcuts_target_actual_gp_after_commission_and_reset_to_automatic() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{
                "row_id": "1",
                "gross_price_per_unit": 600,
                "units": 1,
                "supplier_commission": 20,
                "supplier_currency": "NOK",
                "sales_price_per_unit": 600,
                "sales_currency": "NOK",
            }],
            revision="sales-margin-shortcuts",
        )
    )
    try:
        cell = page.locator('td[data-row-index="0"][data-key="sales_price_per_unit"]')
        cell.click()
        tools = page.locator("#sales-price-tools")
        assert tools.is_visible()

        tools.get_by_role("button", name="20%").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600)
        assert page.evaluate("calculatorState.rows[0].gp_percent") == pytest.approx(0.20)
        assert cell.text_content().strip() == "600.00"

        page.locator("#sales-price-tools").get_by_role("button", name="15%").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(480 / 0.85)
        assert page.evaluate("calculatorState.rows[0].gp_percent") == pytest.approx(0.15, abs=0.00002)
        assert cell.text_content().strip() == "564.71"

        page.locator("#sales-price-tools").get_by_role("button", name="10%").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(480 / 0.9)
        assert page.evaluate("calculatorState.rows[0].gp_percent") == pytest.approx(0.10, abs=0.00002)
        assert cell.text_content().strip() == "533.33"

        page.locator("#sales-price-tools").get_by_role("button", name="Use automatic").click()
        assert page.evaluate("calculatorState.rows[0].sales_price_per_unit") == pytest.approx(600)
        assert page.evaluate("calculatorState.rows[0].gp_percent") == pytest.approx(0.20)
        assert cell.text_content().strip() == "600.00"
    finally:
        browser.close()
        manager.stop()

def test_sales_margin_shortcut_uses_converted_gross_price() -> None:
    payload = _payload(
        [{
            "row_id": "1",
            "gross_price_per_unit": 1200,
            "units": 1,
            "supplier_currency": "NOK",
            "sales_price_per_unit": None,
            "sales_currency": "EUR",
            "_sales_price_per_unit_touched": False,
        }],
        revision="converted-margin",
    )
    payload["currency_rates"] = {"NOK": 1, "EUR": 12}
    manager, browser, page = _browser_page(payload)
    try:
        sales_cell = page.locator('td[data-row-index="0"][data-key="sales_price_per_unit"]')
        sales_cell.click()
        page.get_by_role("button", name="20%").click()

        assert sales_cell.text_content().strip() == "125.00"
        assert page.evaluate("calculatorState.rows[0]._sales_price_per_unit_touched") is True
        assert page.evaluate("calculatorState.rows[0].sales_price_nok_total") == 1500
    finally:
        browser.close()
        manager.stop()
