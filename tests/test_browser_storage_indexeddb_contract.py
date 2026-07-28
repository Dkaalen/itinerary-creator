from __future__ import annotations

import json
import shutil

import pytest

from app_modules.browser_storage_contract import browser_storage_contract
from app_modules.browser_storage_guard import _BROWSER_STORAGE_GUARD
from tests.support.browser_storage_harness import fake_indexed_db_script

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


def test_guard_migrates_owned_payloads_to_indexeddb_and_preserves_unrelated_storage() -> None:
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    contract = browser_storage_contract()
    calc = contract["owners"]["calculator"]
    editor = contract["owners"]["visual_editor"]
    calc_key = f"{calc['current_prefix']}project:test"
    editor_key = f"{editor['current_prefix']}editor-test"
    storage_double = r"""
      <script>
        (() => {
          const local = new Map();
          const session = new Map();
          const api = (store) => ({
            get length() { return store.size; },
            key: (index) => [...store.keys()][Number(index)] ?? null,
            getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
            setItem: (key, value) => store.set(String(key), String(value)),
            removeItem: (key) => store.delete(String(key)),
            clear: () => store.clear(),
          });
          Object.defineProperty(window, 'localStorage', {value: api(local), configurable: true});
          Object.defineProperty(window, 'sessionStorage', {value: api(session), configurable: true});
        })();
      </script>
    """
    preload = f"""
      <script>
        localStorage.setItem({json.dumps(calc_key)}, JSON.stringify({{savedAt: Date.now(), rows: [{{travel_element: 'Hotel'}}]}}));
        localStorage.setItem({json.dumps(calc_key + calc['recovery_suffix'])}, JSON.stringify({{schemaVersion: 4, entries: [{{id: 'v1', savedAt: Date.now(), kind: 'full', rows: []}}]}}));
        localStorage.setItem({json.dumps(editor_key)}, JSON.stringify({{saved_at: Date.now(), model: {{draft_id: 'editor-test'}}}}));
        localStorage.setItem({json.dumps(editor['legacy_prefixes'][0] + 'old')}, 'legacy');
        localStorage.setItem('unrelated.application.key', 'keep');
      </script>
    """
    html = f"<html><body>{storage_double}{fake_indexed_db_script()}{preload}{_BROWSER_STORAGE_GUARD}</body></html>"

    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.wait_for_function(
            "key => sessionStorage.getItem(key) !== null",
            arg=contract["cleanup_session_key"],
        )
        assert page.evaluate("key => localStorage.getItem(key)", calc_key) is None
        assert page.evaluate("key => localStorage.getItem(key)", calc_key + calc["recovery_suffix"]) is None
        assert page.evaluate("key => localStorage.getItem(key)", editor_key) is None
        assert page.evaluate("key => localStorage.getItem(key)", editor["legacy_prefixes"][0] + "old") is None
        assert page.evaluate("localStorage.getItem('unrelated.application.key')") == "keep"
        records = page.evaluate(
            """contract => {
              const state = window.__fakeIndexedDbDatabases.get(contract.indexed_db.name);
              const store = state.stores.get(contract.indexed_db.store);
              return [...store.values()].map(value => ({owner: value.owner, namespace: value.namespace, kind: value.kind, bytes: value.bytes}));
            }""",
            contract,
        )
        assert {(item["owner"], item["kind"]) for item in records} == {
            ("calculator", "draft"),
            ("calculator", "recovery"),
            ("visual_editor", "draft"),
        }
        initial_puts = page.evaluate("Number(window.__fakeIndexedDbPutCount || 0)")
        page.add_script_tag(content=_BROWSER_STORAGE_GUARD.removeprefix("<script>").removesuffix("</script>"))
        page.wait_for_timeout(50)
        assert page.evaluate("Number(window.__fakeIndexedDbPutCount || 0)") == initial_puts
        assert page.evaluate("key => sessionStorage.getItem(key)", contract["cleanup_session_key"]) == str(contract["schema_version"])
    finally:
        browser.close()
        manager.stop()



def test_guard_keeps_current_localstorage_payload_when_indexeddb_migration_fails() -> None:
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    contract = browser_storage_contract()
    calc_key = f"{contract['owners']['calculator']['current_prefix']}project:blocked"
    storage_double = r"""
      <script>
        (() => {
          const local = new Map();
          const session = new Map();
          const api = (store) => ({
            get length() { return store.size; },
            key: (index) => [...store.keys()][Number(index)] ?? null,
            getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
            setItem: (key, value) => store.set(String(key), String(value)),
            removeItem: (key) => store.delete(String(key)),
            clear: () => store.clear(),
          });
          Object.defineProperty(window, 'localStorage', {value: api(local), configurable: true});
          Object.defineProperty(window, 'sessionStorage', {value: api(session), configurable: true});
        })();
      </script>
    """
    preload = f"""
      <script>
        localStorage.setItem({json.dumps(calc_key)}, JSON.stringify({{savedAt: Date.now(), rows: [{{travel_element: 'Keep me'}}]}}));
        localStorage.setItem('unrelated.application.key', 'keep');
        window.__failFakeIndexedDbWrites = true;
      </script>
    """
    html = f"<html><body>{storage_double}{fake_indexed_db_script()}{preload}{_BROWSER_STORAGE_GUARD}</body></html>"

    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.wait_for_function("Number(window.__fakeIndexedDbPutAttemptCount || 0) >= 1")
        page.wait_for_timeout(50)
        assert "Keep me" in page.evaluate("key => localStorage.getItem(key)", calc_key)
        assert page.evaluate("localStorage.getItem('unrelated.application.key')") == "keep"
        assert page.evaluate("key => sessionStorage.getItem(key)", contract["cleanup_session_key"]) is None
    finally:
        browser.close()
        manager.stop()


def test_guard_counts_paired_calculator_versions_when_pruning_indexeddb_budget() -> None:
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    contract = browser_storage_contract()
    calc = contract["owners"]["calculator"]
    old_key = f"{calc['current_prefix']}project:old-large-history"
    active_key = f"{calc['current_prefix']}project:active"
    storage_double = r"""
      <script>
        (() => {
          const local = new Map();
          const session = new Map();
          const api = (store) => ({
            get length() { return store.size; },
            key: (index) => [...store.keys()][Number(index)] ?? null,
            getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
            setItem: (key, value) => store.set(String(key), String(value)),
            removeItem: (key) => store.delete(String(key)),
            clear: () => store.clear(),
          });
          Object.defineProperty(window, 'localStorage', {value: api(local), configurable: true});
          Object.defineProperty(window, 'sessionStorage', {value: api(session), configurable: true});
        })();
      </script>
    """
    preload = f"""
      <script>
        const oldSavedAt = Date.now() - 1000;
        localStorage.setItem({json.dumps(old_key)}, JSON.stringify({{savedAt: oldSavedAt, rows: [{{}}]}}));
        localStorage.setItem(
          {json.dumps(old_key + calc['recovery_suffix'])},
          JSON.stringify({{schemaVersion: 4, entries: [{{id: 'old', savedAt: oldSavedAt, kind: 'full', rows: [{{comments: 'x'.repeat(1600000)}}]}}]}})
        );
        localStorage.setItem({json.dumps(active_key)}, JSON.stringify({{savedAt: Date.now(), rows: [{{travel_element: 'Active'}}]}}));
      </script>
    """
    html = f"<html><body>{storage_double}{fake_indexed_db_script()}{preload}{_BROWSER_STORAGE_GUARD}</body></html>"

    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.wait_for_function(
            "key => sessionStorage.getItem(key) !== null",
            arg=contract["cleanup_session_key"],
        )
        records = page.evaluate(
            """contract => {
              const state = window.__fakeIndexedDbDatabases.get(contract.indexed_db.name);
              const store = state.stores.get(contract.indexed_db.store);
              return [...store.values()].map(value => ({namespace: value.namespace, kind: value.kind}));
            }""",
            contract,
        )
        assert {(item["namespace"], item["kind"]) for item in records} == {(active_key, "draft")}
    finally:
        browser.close()
        manager.stop()
