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


def test_trip_start_shifts_linked_dates_and_preserves_locked_dates_with_one_undo() -> None:
    rows = [
        {
            "row_id": "1", "day": "Day 1", "from_date": "01.01.2026",
            "from_date_mode": "linked", "from_date_offset": 0,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
        {
            "row_id": "2", "day": "Day 2", "from_date": "02.01.2026", "to_date": "05.01.2026",
            "from_date_mode": "linked", "from_date_offset": 1,
            "to_date_mode": "linked", "to_date_offset": 4,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
        {
            "row_id": "3", "day": "Day 3", "from_date": "15.01.2026",
            "from_date_mode": "locked", "from_date_offset": None,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
    ]
    manager, browser, page = _browser_page(
        _payload(rows, revision="trip-start-shift", trip_start_date="2026-01-01")
    )
    try:
        trip_start = page.locator('[data-action="set-trip-start"]')
        trip_start.fill("2026-02-01")
        trip_start.dispatch_event("change")

        assert page.evaluate("calculatorState.tripStartDate") == "2026-02-01"
        assert page.evaluate("calculatorState.rows[0].from_date") == "01.02.2026"
        assert page.evaluate("calculatorState.rows[1].from_date") == "02.02.2026"
        assert page.evaluate("calculatorState.rows[1].to_date") == "05.02.2026"
        assert page.evaluate("calculatorState.rows[2].from_date") == "15.01.2026"

        page.get_by_role("button", name="Undo").click()
        assert page.evaluate("calculatorState.tripStartDate") == "2026-01-01"
        assert page.evaluate("calculatorState.rows[1].from_date") == "02.01.2026"
        assert page.evaluate("calculatorState.rows[1].to_date") == "05.01.2026"
    finally:
        browser.close()
        manager.stop()


def test_manual_date_edit_locks_cell_and_link_dates_rejoins_trip_sequence() -> None:
    rows = [
        {
            "row_id": "1", "day": "Day 1", "from_date": "01.01.2026",
            "from_date_mode": "linked", "from_date_offset": 0,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
        {
            "row_id": "2", "day": "Day 2", "from_date": "02.01.2026",
            "from_date_mode": "linked", "from_date_offset": 1,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
    ]
    manager, browser, page = _browser_page(
        _payload(rows, revision="date-lock-relink", trip_start_date="2026-01-01")
    )
    try:
        date_cell = page.locator('td[data-row-index="1"][data-key="from_date"]')
        date_cell.click()
        date_cell.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("10.01.2026")
        page.keyboard.press("Tab")

        assert page.evaluate("calculatorState.rows[1].from_date_mode") == "locked"
        assert date_cell.get_attribute("title").startswith("Locked date")

        trip_start = page.locator('[data-action="set-trip-start"]')
        trip_start.fill("2026-02-01")
        trip_start.dispatch_event("change")
        assert page.evaluate("calculatorState.rows[1].from_date") == "10.01.2026"

        date_cell.click()
        page.locator(".calculator-toolbar-more > summary").click()
        page.get_by_role("button", name="Link dates").click()
        assert page.evaluate("calculatorState.rows[1].from_date_mode") == "linked"
        assert page.evaluate("calculatorState.rows[1].from_date") == "02.02.2026"
    finally:
        browser.close()
        manager.stop()


def test_dashboard_presents_eur_first_and_retains_nok_as_secondary_context() -> None:
    payload = _payload(
        [{
            "row_id": "1",
            "gross_price_per_unit": 1200,
            "units": 1,
            "supplier_currency": "NOK",
            "sales_price_per_unit": 1800,
            "sales_currency": "NOK",
        }],
        revision="eur-first-dashboard",
    )
    payload["currency_rates"] = {"NOK": 1, "EUR": 12}
    manager, browser, page = _browser_page(payload)
    try:
        dashboard_text = page.locator(".calculator-dashboard").inner_text()
        assert "Total cost EUR\n€100.00\nNOK 1,200.00" in dashboard_text
        assert "Total sales EUR\n€150.00\nNOK 1,800.00" in dashboard_text
        assert "Profit / GP EUR\n€50.00\nNOK 600.00" in dashboard_text
        assert "Total cost NOK" not in dashboard_text
    finally:
        browser.close()
        manager.stop()



def test_editing_day_one_date_updates_trip_start_and_all_linked_dates() -> None:
    rows = [
        {
            "row_id": "1", "day": "Day 1", "from_date": "01.01.2026",
            "from_date_mode": "linked", "from_date_offset": 0,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
        {
            "row_id": "2", "day": "Day 2", "from_date": "02.01.2026", "to_date": "04.01.2026",
            "from_date_mode": "linked", "from_date_offset": 1,
            "to_date_mode": "linked", "to_date_offset": 3,
            "supplier_currency": "NOK", "sales_currency": "EUR",
        },
    ]
    manager, browser, page = _browser_page(
        _payload(rows, revision="day-one-authority", trip_start_date="2026-01-01")
    )
    try:
        page.evaluate(
            """() => {
                recordHistory();
                updateRowValue(0, 'from_date', '10.02.2026', false);
                markLocalDraft();
                rerender({skipCalculation: true});
            }"""
        )

        assert page.locator('[data-action="set-trip-start"]').input_value() == "2026-02-10"
        assert page.evaluate("calculatorState.tripStartDate") == "2026-02-10"
        assert page.evaluate("calculatorState.rows[0].from_date") == "10.02.2026"
        assert page.evaluate("calculatorState.rows[1].from_date") == "11.02.2026"
        assert page.evaluate("calculatorState.rows[1].to_date") == "13.02.2026"

        page.get_by_role("button", name="Undo").click()
        assert page.evaluate("calculatorState.tripStartDate") == "2026-01-01"
        assert page.evaluate("calculatorState.rows[1].from_date") == "02.01.2026"
        assert page.evaluate("calculatorState.rows[1].to_date") == "04.01.2026"
    finally:
        browser.close()
        manager.stop()
