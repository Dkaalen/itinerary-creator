from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1] / "calculator_grid_component" / "frontend"


def _html() -> str:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles" / "calculator_grid.css").read_text(encoding="utf-8")
    scripts = "".join(
        f"<script>{(ROOT / source).read_text(encoding='utf-8')}</script>"
        for source in re.findall(r'<script src="([^"]+)"', index)
    )
    storage = """<script>
      (() => {
        const localStore = new Map();
        const sessionStore = new Map();
        const storageApi = (store) => ({
          getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
          setItem: (key, value) => store.set(String(key), String(value)),
          removeItem: (key) => store.delete(String(key)),
          clear: () => store.clear()
        });
        Object.defineProperty(window, 'localStorage', {value: storageApi(localStore)});
        Object.defineProperty(window, 'sessionStorage', {value: storageApi(sessionStore)});
      })();
    </script>"""
    return f"<html><head><style>{css}</style></head><body><div id='root'></div>{storage}{scripts}</body></html>"


def _payload(*, revision: str = "recovery-test") -> dict:
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
    }


def _browser_page(*, revision: str = "recovery-test"):
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_content(_html(), wait_until="load")
    payload = _payload(revision=revision)
    page.evaluate(
        "payload => window.dispatchEvent(new MessageEvent('message', {data: {type: 'streamlit:render', args: {payload}}}))",
        payload,
    )
    page.wait_for_selector('td[data-key="travel_element"]')
    return manager, browser, page, payload


def _install_storage_quota(page, limit_bytes: int) -> None:
    page.evaluate(
        """limitBytes => {
          const originalSetItem = window.localStorage.setItem.bind(window.localStorage);
          const originalRemoveItem = window.localStorage.removeItem.bind(window.localStorage);
          const knownKeys = () => [getCalculatorDraftStorageKey(), calculatorRecoveryStorageKey()];
          window.localStorage.setItem = (key, value) => {
            const candidateKey = String(key);
            const candidateValue = String(value);
            let total = 0;
            for (const knownKey of knownKeys()) {
              const storedValue = knownKey === candidateKey
                ? candidateValue
                : (window.localStorage.getItem(knownKey) || '');
              if (storedValue) total += (knownKey.length + storedValue.length) * 2;
            }
            if (total > limitBytes) {
              throw new DOMException('Storage quota exceeded', 'QuotaExceededError');
            }
            originalSetItem(candidateKey, candidateValue);
          };
          window.localStorage.removeItem = (key) => originalRemoveItem(String(key));
        }""",
        limit_bytes,
    )


def test_recovery_storage_uses_compact_hashes_and_row_deltas() -> None:
    manager, browser, page, payload = _browser_page(revision="compact-delta")
    try:
        page.evaluate(
            """() => {
              calculatorState.rows = Array.from({length: 10}, (_, index) => ({
                row_id: String(index + 1),
                travel_element: `Original service ${index}`,
                comments: 'baseline '.repeat(20),
                gross_price_per_unit: 100,
                units: 1,
                supplier_currency: 'NOK',
                sales_currency: 'NOK'
              }));
              saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, 'expanded');
              calculatorState.rows[0].travel_element = 'Updated service';
              markLocalDraft(false);
              flushRecoverySnapshot('edited');
            }"""
        )
        stored = page.evaluate(
            "key => JSON.parse(window.localStorage.getItem(`${key}.versions`))",
            payload["draft_storage_key"],
        )

        assert stored["schemaVersion"] == 4
        assert stored["entries"][0]["kind"] == "full"
        assert len(stored["entries"][0]["hash"]) == 16
        assert "signature" not in stored["entries"][0]
        assert stored["entries"][1]["kind"] == "delta"
        assert "rows" not in stored["entries"][1]
        assert stored["entries"][1]["rowChanges"]

        snapshots = page.evaluate("loadCalculatorRecoverySnapshots()")
        assert snapshots[0]["rows"][0]["travel_element"] == "Updated service"
        assert snapshots[1]["rows"][0]["travel_element"] == "Original service 0"
        legacy_size = page.evaluate(
            """snapshots => JSON.stringify(snapshots.map((snapshot) => ({
              ...snapshot,
              signature: JSON.stringify(calculatorRecoveryComparable(snapshot))
            }))).length""",
            snapshots,
        )
        compact_size = page.evaluate("window.localStorage.getItem(calculatorRecoveryStorageKey()).length")
        assert compact_size < legacy_size

        page.get_by_role("button", name=re.compile(r"Versions \(\d+\)")).click()
        assert "stored in this browser" in page.locator(".calculator-version-heading").text_content()
    finally:
        browser.close()
        manager.stop()


def test_large_projects_adapt_retention_and_preserve_long_values() -> None:
    manager, browser, page, _payload_data = _browser_page(revision="large-recovery")
    try:
        rows = [
            {
                "row_id": str(index + 1),
                "travel_element": f"Service {index}",
                "comments": (f"Long comment {index} " + "x" * 8000),
                "url": "https://example.com/" + ("path/" * 160) + str(index),
                "gross_price_per_unit": "=100/10*0.8",
                "units": 1,
                "supplier_currency": "NOK",
                "sales_currency": "NOK",
            }
            for index in range(93)
        ]
        page.evaluate(
            """rows => {
              calculatorState.rows = rows;
              for (let index = 0; index < 7; index += 1) {
                calculatorState.rows[0].comments = `${rows[0].comments}-${index}`;
                saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, `large-${index}`);
              }
              calculatorState.recoverySnapshots = loadCalculatorRecoverySnapshots();
            }""",
            rows,
        )

        snapshots = page.evaluate("loadCalculatorRecoverySnapshots()")
        assert 1 <= len(snapshots) <= 4
        assert snapshots[0]["rows"][92]["gross_price_per_unit"] == "=100/10*0.8"
        assert snapshots[0]["rows"][92]["url"].endswith("92")
        assert snapshots[0]["rows"][92]["comments"].startswith("Long comment 92")
        assert page.evaluate("calculatorRecoveryStorageUsage().totalBytes") > 500_000
    finally:
        browser.close()
        manager.stop()


def test_quota_prunes_old_versions_before_current_draft() -> None:
    manager, browser, page, payload = _browser_page(revision="quota-prune")
    try:
        page.evaluate(
            """() => {
              calculatorState.rows[0].travel_element = 'Version two';
              saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, 'second');
            }"""
        )
        _install_storage_quota(page, 17_500)
        long_comment = "current-draft-" + "z" * 8000
        saved = page.evaluate(
            """comment => {
              calculatorState.rows[0].comments = comment;
              return saveCalculatorDraft(calculatorState, activeBackendRevision);
            }""",
            long_comment,
        )

        assert saved is True
        draft = page.evaluate(
            "key => JSON.parse(window.localStorage.getItem(key))",
            payload["draft_storage_key"],
        )
        assert draft["rows"][0]["comments"] == long_comment
        assert page.evaluate("window.localStorage.getItem(calculatorRecoveryStorageKey())") is None
        assert page.evaluate("calculatorState.recoverySnapshots.length") == 0
        assert page.get_by_role("button", name="Versions (0)").count() == 1
        assert "removed to protect" in page.locator("#calculator-recovery-warning").text_content()
    finally:
        browser.close()
        manager.stop()


def test_unavailable_storage_shows_one_clear_warning() -> None:
    manager, browser, page, _payload_data = _browser_page(revision="quota-warning")
    try:
        _install_storage_quota(page, 2_000)
        saved = page.evaluate(
            """() => {
              calculatorState.rows[0].comments = 'q'.repeat(12000);
              return saveCalculatorDraft(calculatorState, activeBackendRevision);
            }"""
        )

        assert saved is False
        warning = page.locator("#calculator-recovery-warning")
        assert warning.count() == 1
        assert "could not be protected locally" in warning.text_content()
    finally:
        browser.close()
        manager.stop()


def test_legacy_recovery_arrays_remain_readable() -> None:
    manager, browser, page, _payload_data = _browser_page(revision="legacy-recovery")
    try:
        snapshots = page.evaluate("loadCalculatorRecoverySnapshots()")
        legacy = [{key: value for key, value in snapshots[0].items() if key != "hash"}]
        page.evaluate(
            "legacy => window.localStorage.setItem(calculatorRecoveryStorageKey(), JSON.stringify(legacy))",
            legacy,
        )

        restored = page.evaluate("loadCalculatorRecoverySnapshots()")
        assert restored[0]["rows"][0]["travel_element"] == "Original service"
        assert len(restored[0]["hash"]) == 16
    finally:
        browser.close()
        manager.stop()
