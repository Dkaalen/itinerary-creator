"""Bounded Chromium harness for the Project Explorer component."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "project_explorer_component" / "frontend"


def project_explorer_frontend_html() -> str:
    index = (FRONTEND_ROOT / "index.html").read_text(encoding="utf-8")
    css = (FRONTEND_ROOT / "styles" / "project_explorer.css").read_text(encoding="utf-8")
    scripts = "".join(
        f"<script>{(FRONTEND_ROOT / source).read_text(encoding='utf-8')}</script>"
        for source in re.findall(r'<script src="([^"]+)"', index)
    )
    storage = """
      <script>
        (() => {
          const store = new Map();
          const api = {
            get length() { return store.size; },
            key: (index) => [...store.keys()][Number(index)] ?? null,
            getItem: (key) => store.has(String(key)) ? store.get(String(key)) : null,
            setItem: (key, value) => store.set(String(key), String(value)),
            removeItem: (key) => store.delete(String(key)),
            clear: () => store.clear(),
          };
          Object.defineProperty(window, 'sessionStorage', {value: api});
        })();
      </script>
    """
    capture = """
      <script>
        window.__projectExplorerMessages = [];
        window.addEventListener('message', (event) => {
          if (event?.data?.type?.startsWith?.('streamlit:')) {
            window.__projectExplorerMessages.push(event.data);
          }
        });
      </script>
    """
    return f"<html><head><style>{css}</style></head><body><div id='root'></div>{storage}{capture}{scripts}</body></html>"


def project_explorer_payload(*, revision: int = 0, selected_ids: list[str] | None = None) -> dict[str, Any]:
    rows = [
        {
            "id": "project-1",
            "name": "Norway Explorer",
            "owner": "Dennis",
            "folder": "ITIN-1001",
            "last_saved": "Today at 12:00",
            "is_open": False,
        },
        {
            "id": "project-2",
            "name": "Iceland Winter",
            "owner": "Vipin",
            "folder": "ITIN-1002",
            "last_saved": "Yesterday",
            "is_open": True,
        },
        {
            "id": "project-3",
            "name": "Sweden Summer",
            "owner": "Christer",
            "folder": "—",
            "last_saved": "3 days ago",
            "is_open": False,
        },
    ]
    selected = list(selected_ids or [])
    return {
        "rows": rows,
        "selected_project_ids": selected,
        "selected_projects": [row for row in rows if row["id"] in selected],
        "list_revision": revision,
        "selection_session_id": "browser-test-session",
        "page_index": 0,
        "page_number": 1,
        "has_previous": False,
        "has_next": True,
        "first_item_number": 1,
        "last_item_number": 3,
        "total_count": 28,
        "total_pages": 10,
    }


def open_project_explorer_browser_page(payload: dict[str, Any] | None = None):
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_content(project_explorer_frontend_html(), wait_until="load")
    render_payload = payload or project_explorer_payload()
    page.evaluate(
        "payload => window.dispatchEvent(new MessageEvent('message', "
        "{data: {type: 'streamlit:render', args: {payload}}}))",
        render_payload,
    )
    page.wait_for_selector(".project-explorer-shell")
    return manager, browser, page, render_payload


def component_values(page) -> list[dict[str, Any]]:
    return page.evaluate(
        "() => window.__projectExplorerMessages"
        ".filter(message => message.type === 'streamlit:setComponentValue')"
        ".map(message => message.value)"
    )


def wait_for_component_values(page, count: int = 1) -> list[dict[str, Any]]:
    page.wait_for_function(
        "expected => window.__projectExplorerMessages"
        ".filter(message => message.type === 'streamlit:setComponentValue').length >= expected",
        arg=count,
    )
    return component_values(page)
