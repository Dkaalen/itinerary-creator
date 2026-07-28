"""Shared Chromium harness for bounded Calculator browser workflow tests."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from app_modules.browser_storage_contract import browser_storage_contract
from calculator.financial_rules import financial_rules_payload
from calculator.library_ranking import local_library_ranking_spec_payload
from tests.support.browser_storage_harness import fake_indexed_db_script

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "calculator_grid_component" / "frontend"


def calculator_frontend_html() -> str:
    """Return the production Calculator frontend with scripts embedded in page order."""

    index = (FRONTEND_ROOT / "index.html").read_text(encoding="utf-8")
    css = (FRONTEND_ROOT / "styles" / "calculator_grid.css").read_text(encoding="utf-8")
    scripts = "".join(
        f"<script>{(FRONTEND_ROOT / source).read_text(encoding='utf-8')}</script>"
        for source in re.findall(r'<script src="([^"]+)"', index)
    )
    storage = """<script>
      (() => {
        const localStore = new Map();
        const sessionStore = new Map();
        const storageApi = (store) => ({
          get length() { return store.size; },
          key: (index) => [...store.keys()][Number(index)] ?? null,
          getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
          setItem: (key, value) => store.set(String(key), String(value)),
          removeItem: (key) => store.delete(String(key)),
          clear: () => store.clear()
        });
        Object.defineProperty(window, 'localStorage', {value: storageApi(localStore)});
        Object.defineProperty(window, 'sessionStorage', {value: storageApi(sessionStore)});
      })();
    </script>"""
    return f"<html><head><style>{css}</style></head><body><div id='root'></div>{storage}{fake_indexed_db_script()}{scripts}</body></html>"


def calculator_payload(
    rows: list[dict[str, Any]],
    *,
    library_rows: list[dict[str, Any]] | None = None,
    revision: str = "browser-test",
) -> dict[str, Any]:
    """Build the normal production-like payload used by browser interaction tests."""

    return {
        "rows": rows,
        "number_of_pax": None,
        "state_revision": revision,
        "draft_storage_key": f"calculator.browser.test.{revision}",
        "show_advanced": False,
        "currency_rates": {"NOK": 1, "EUR": 12},
        "financial_rules": financial_rules_payload(),
        "library_status": "Ready",
        "library_rows": library_rows or [],
        "library_ranking_spec": local_library_ranking_spec_payload(),
        "browser_storage_contract": browser_storage_contract(),
    }


def open_blank_calculator_browser_page():
    """Launch Chromium with the Calculator assets loaded but no backend render yet."""

    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_content(calculator_frontend_html(), wait_until="load")
    return manager, browser, page


def open_calculator_browser_page(payload: dict[str, Any]):
    """Launch Chromium, render the Calculator component, and return owned resources."""

    manager, browser, page = open_blank_calculator_browser_page()
    page.evaluate(
        "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
        payload,
    )
    page.wait_for_selector('td[data-key="travel_element"]')
    return manager, browser, page


def recovery_payload(*, revision: str = "recovery-test") -> dict[str, Any]:
    """Build the historical recovery fixture payload without altering its contract."""

    return {
        "rows": [{
            "row_id": "1",
            "travel_element": "Original service",
            "supplier_currency": "NOK",
            "sales_currency": "NOK",
            "gross_price_per_unit": 100,
            "units": 1,
        }],
        "number_of_pax": None,
        "state_revision": revision,
        "draft_storage_key": f"calculator.browser.test.{revision}",
        "show_advanced": False,
        "currency_rates": {"NOK": 1, "EUR": 12},
        "library_status": "Ready",
        "library_rows": [],
        "library_ranking_spec": local_library_ranking_spec_payload(),
        "browser_storage_contract": browser_storage_contract(),
    }


def open_recovery_browser_page(*, revision: str = "recovery-test"):
    """Launch the recovery fixture and return resources plus the rendered payload."""

    payload = recovery_payload(revision=revision)
    manager, browser, page = open_calculator_browser_page(payload)
    return manager, browser, page, payload
