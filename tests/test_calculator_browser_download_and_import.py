from __future__ import annotations

import re

import pytest

from support.calculator_browser_harness import (
    calculator_payload as _payload,
    open_calculator_browser_page as _browser_page,
)


def test_explicit_download_submits_the_latest_unsynced_browser_state() -> None:
    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "type": "", "travel_element": "", "supplier_currency": "NOK", "sales_currency": "NOK"}],
            revision="explicit-submit",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(JSON.parse(event.data.value));
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Arrival")
        page.get_by_role("button", name="Download Excel").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")

        values = page.evaluate("window.__calculatorComponentValues")
        assert len(values) == 1
        assert values[0]["action"] == "download"
        assert values[0]["rows"][0]["type"] == "Arrival"
    finally:
        browser.close()
        manager.stop()

def test_prepared_excel_downloads_from_the_grid_toolbar() -> None:
    import base64

    payload = _payload(
        [{"row_id": "1", "travel_element": "Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="prepared-excel",
    )
    payload["pending_download"] = {
        "filename": "Oslo Trip.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": base64.b64encode(b"xlsx-test-content").decode("ascii"),
    }
    manager, browser, page = _browser_page(payload)
    try:
        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download Excel").click()
        download = download_info.value

        assert download.suggested_filename == "Oslo Trip.xlsx"
        assert page.locator("#calculator-sync-status").text_content() == "Excel downloaded"
    finally:
        browser.close()
        manager.stop()

def test_editing_after_excel_is_prepared_invalidates_the_stale_browser_download() -> None:
    import base64

    payload = _payload(
        [{"row_id": "1", "type": "Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="invalidate-prepared-excel",
    )
    payload["pending_download"] = {
        "filename": "Old.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": base64.b64encode(b"old").decode("ascii"),
    }
    manager, browser, page = _browser_page(payload)
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(JSON.parse(event.data.value));
                    }
                });
            }"""
        )
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Transfer")

        assert page.evaluate("calculatorState.pendingDownload") is None
        assert page.locator("#calculator-excel-ready-status").count() == 0

        page.get_by_role("button", name="Download Excel").click()
        page.wait_for_function("window.__calculatorComponentValues.length === 1")
        values = page.evaluate("window.__calculatorComponentValues")
        assert len(values) == 1
        assert values[0]["action"] == "download"
        assert values[0]["rows"][0]["type"] == "Transfer"
    finally:
        browser.close()
        manager.stop()

def test_same_revision_backend_rerender_cannot_restore_a_stale_excel_download() -> None:
    import base64

    payload = _payload(
        [{"row_id": "1", "type": "Hotel", "supplier_currency": "NOK", "sales_currency": "NOK"}],
        revision="stale-download-rerender",
    )
    payload["pending_download"] = {
        "filename": "Old.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": base64.b64encode(b"old").decode("ascii"),
    }
    manager, browser, page = _browser_page(payload)
    try:
        cell = page.locator('td[data-row-index="0"][data-key="type"]')
        cell.click()
        page.keyboard.type("Transfer")
        assert page.evaluate("calculatorState.pendingDownload") is None

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            payload,
        )

        assert page.evaluate("calculatorState.rows[0].type") == "Transfer"
        assert page.evaluate("calculatorState.pendingDownload") is None
        assert page.locator("#calculator-excel-ready-status").count() == 0
    finally:
        browser.close()
        manager.stop()

def test_open_excel_sends_file_bytes_to_the_backend_action() -> None:
    import base64

    manager, browser, page = _browser_page(
        _payload(
            [{"row_id": "1", "supplier_currency": "NOK", "sales_currency": "EUR"}],
            revision="open-excel",
        )
    )
    try:
        page.evaluate(
            """() => {
                window.__calculatorComponentValues = [];
                window.addEventListener('message', (event) => {
                    if (event.data?.type === 'streamlit:setComponentValue') {
                        window.__calculatorComponentValues.push(JSON.parse(event.data.value));
                    }
                });
            }"""
        )
        page.locator('[data-action="excel-file-input"]').set_input_files(
            {
                "name": "Imported Trip.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "buffer": b"PK\x03\x04test-workbook",
            }
        )
        page.wait_for_function("window.__calculatorComponentValues.length === 1")

        value = page.evaluate("window.__calculatorComponentValues[0]")
        assert value["action"] == "open_excel"
        assert value["upload_filename"] == "Imported Trip.xlsx"
        assert value["upload_content_base64"] == base64.b64encode(b"PK\x03\x04test-workbook").decode("ascii")
    finally:
        browser.close()
        manager.stop()

def test_prepared_excel_auto_downloads_once_per_signature() -> None:
    import base64

    initial = _payload(
        [{"row_id": "1", "travel_element": "Hotel", "supplier_currency": "NOK", "sales_currency": "EUR"}],
        revision="auto-download-initial",
    )
    manager, browser, page = _browser_page(initial)
    downloads: list[str] = []
    page.on("download", lambda download: downloads.append(download.suggested_filename))
    try:
        prepared = _payload(initial["rows"], revision="auto-download-prepared")
        prepared["pending_download"] = {
            "filename": "Immediate.xlsx",
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content_base64": base64.b64encode(b"fast-xlsx").decode("ascii"),
            "download_signature": "signature-1",
        }
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            prepared,
        )
        page.wait_for_timeout(300)
        assert downloads == ["Immediate.xlsx"]
        assert page.locator("#calculator-sync-status").text_content() == "Excel downloaded"

        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
            prepared,
        )
        page.wait_for_timeout(300)
        assert downloads == ["Immediate.xlsx"]
    finally:
        browser.close()
        manager.stop()
