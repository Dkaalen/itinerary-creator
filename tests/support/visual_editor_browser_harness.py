"""Bounded Chromium harness for the production visual-editor frontend modules."""

from __future__ import annotations

import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "visual_editor_component" / "frontend"


def visual_editor_bootstrap_script_names() -> tuple[str, ...]:
    """Return the runtime assets in the production bootstrap order."""

    source = (FRONTEND_ROOT / "js" / "editor_bootstrap.js").read_text(encoding="utf-8")
    return tuple(re.findall(r"'js/([^']+\.js)'", source))


def visual_editor_frontend_html() -> str:
    """Embed production modules in bootstrap order for a navigation-free browser test."""

    namespace = (FRONTEND_ROOT / "js" / "editor_namespace.js").read_text(encoding="utf-8")
    scripts = [
        (FRONTEND_ROOT / "js" / name).read_text(encoding="utf-8")
        for name in visual_editor_bootstrap_script_names()
    ]
    css_chunks = [
        path.read_text(encoding="utf-8")
        for path in sorted((FRONTEND_ROOT / "styles").glob("*.css"))
    ]
    embedded_scripts = "".join(f"<script>{source}</script>" for source in (namespace, *scripts))
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
          Object.defineProperty(window, 'localStorage', {value: api});
          Object.defineProperty(window, 'sessionStorage', {value: api});
        })();
      </script>
    """
    startup = """
      <script>
        window.__visualEditorMessages = [];
        window.addEventListener('message', (event) => {
          if (event?.data?.type?.startsWith?.('streamlit:')) window.__visualEditorMessages.push(event.data);
        });
        ItineraryVisualEditor.require('autosave').initialize();
        ItineraryVisualEditor.require('bridge').initialize();
        ItineraryVisualEditor.markReady();
      </script>
    """
    return (
        "<html><head><style>"
        + "\n".join(css_chunks)
        + "</style></head><body><div id='root'></div>"
        + storage
        + embedded_scripts
        + startup
        + "</body></html>"
    )


def visual_editor_payload() -> dict[str, Any]:
    """Build a small production-shaped RenderDocument editor payload."""

    return {
        "draft_id": "visual-editor-browser-test",
        "brand": {
            "company_name": "Booknordics",
            "cover_background": "#0f3438",
            "accent_color": "#c58a24",
        },
        "meta": {
            "source_signature": "visual-editor-browser-signature",
            "draft_schema_version": 1,
        },
        "workflow": {"pictures_added": False, "commit_signal_only": False},
        "cover": {
            "trip_title": "Nordic Escape",
            "trip_dates": "1–3 September 2026",
            "route_label": "Route",
            "destinations_line": "Oslo · Bergen",
            "traveller_line": "2 travellers",
        },
        "summary": {
            "trip_intro": "A compact journey from Oslo to Bergen.",
            "trip_glance": {"Start": "Oslo", "Finish": "Bergen"},
            "journey_arc": [
                {"chapter": "City arrival", "days": "Day 1", "experience": "Discover Oslo"},
                {"chapter": "Westbound journey", "days": "Day 2", "experience": "Travel to Bergen"},
            ],
            "journey_arc_columns": {
                "chapter": "Chapter",
                "days": "Days",
                "experience": "What You’ll Experience",
            },
        },
        "days": [
            {
                "day": "Day 1",
                "city": "Oslo",
                "date": "1 September 2026",
                "title": "Arrival in Oslo",
                "intro": "Arrive in Oslo and settle into the city.",
                "blocks_html": "<div><strong>Hotel:</strong> Central Hotel</div>",
                "image": {},
            },
            {
                "day": "Day 2",
                "city": "Bergen",
                "date": "2 September 2026",
                "title": "Journey to Bergen",
                "intro": "Travel west to Bergen.",
                "blocks_html": "<div><strong>Transport:</strong> Scenic rail journey</div>",
                "image": {},
            },
        ],
        "final_pages": {
            "whats_included_title": "What's included",
            "whats_included_pages_html": [{"html": "<ul><li>Hotels</li></ul>"}],
            "whats_not_included_title": "What's not included",
            "whats_not_included_html": "<ul><li>Flights</li></ul>",
            "important_travel_notes_title": "Important travel notes",
            "important_travel_notes_text": "Times remain subject to confirmation.",
        },
        "document_pages": [],
        "source_rows": {},
        "generated_values": {},
        "warnings": [],
    }


def open_visual_editor_browser_page(payload: dict[str, Any] | None = None):
    """Launch Chromium, initialize the editor modules, and render a payload."""

    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_content(visual_editor_frontend_html(), wait_until="load")
    page.wait_for_function("window.ItineraryVisualEditor?.isReady() === true")
    page.evaluate("window.localStorage.setItem('itineraryEditorDebug', '1')")
    render_payload = payload or visual_editor_payload()
    page.evaluate(
        "payload => window.dispatchEvent(new MessageEvent('message', "
        "{data: {type: 'streamlit:render', args: {payload}}}))",
        render_payload,
    )
    page.wait_for_selector(".editor-shell")
    return manager, browser, page, render_payload


def open_bootstrapped_visual_editor_browser_page():
    """Launch the real index and dynamic bootstrap through intercepted local assets."""

    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    requested_assets: list[str] = []
    page_errors: list[str] = []

    def fulfill_local_asset(route) -> None:
        url = route.request.url
        relative = url.split("https://visual-editor.test/", 1)[1].split("?", 1)[0]
        requested_assets.append(relative)
        path = (FRONTEND_ROOT / relative).resolve()
        if FRONTEND_ROOT not in path.parents and path != FRONTEND_ROOT:
            route.fulfill(status=404, body="Not found")
            return
        if not path.exists() or path.is_dir():
            route.fulfill(status=404, body="Not found")
            return
        route.fulfill(
            status=200,
            body=path.read_bytes(),
            content_type=mimetypes.guess_type(path.name)[0] or "text/plain",
        )

    page.route("https://visual-editor.test/**", fulfill_local_asset)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    index = (FRONTEND_ROOT / "index.html").read_text(encoding="utf-8")
    index = index.replace("<head>", '<head><base href="https://visual-editor.test/">', 1)
    page.set_content(index, wait_until="load")
    page.wait_for_function("window.ItineraryVisualEditor?.isReady() === true")
    return manager, browser, page, requested_assets, page_errors
