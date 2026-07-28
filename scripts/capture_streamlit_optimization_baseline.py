"""Capture real Streamlit startup, storage and computed-style evidence.

Run against a local or authorized hosted app. The script is read-only: it does
not save, open, select or delete projects. Browser-storage values are never
written to the report; only key names and byte counts are recorded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

DEFAULT_VIEWPORTS = ((1440, 1000), (1024, 900), (768, 900))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Running Streamlit app URL.")
    parser.add_argument("--output-dir", type=Path, default=Path("qa_reports/optimization_baseline"))
    parser.add_argument("--storage-fill-mb", type=float, default=0.0)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Install requirements-dev.txt and Playwright Chromium first.") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "url": args.url,
        "storage_fill_mb": max(0.0, args.storage_fill_mb),
        "viewports": [],
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        try:
            for width, height in DEFAULT_VIEWPORTS:
                report["viewports"].append(
                    _capture_viewport(
                        browser,
                        url=args.url,
                        output_dir=args.output_dir,
                        width=width,
                        height=height,
                        storage_fill_mb=max(0.0, args.storage_fill_mb),
                    )
                )
        finally:
            browser.close()

    report_path = args.output_dir / "baseline.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report_path)
    return 0


def _capture_viewport(
    browser: Any,
    *,
    url: str,
    output_dir: Path,
    width: int,
    height: int,
    storage_fill_mb: float,
) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": width, "height": height})
    if storage_fill_mb:
        context.add_init_script(_storage_fill_script(storage_fill_mb))
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text[:500]) if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)[:500]))

    started = perf_counter()
    response_status = None
    navigation_error = ""
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        response_status = response.status if response else None
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=12_000)
    except Exception as exc:
        navigation_error = f"{type(exc).__name__}: {exc}"[:500]
    load_seconds = perf_counter() - started

    screenshot_name = f"{width}x{height}-startup.png"
    try:
        page.screenshot(path=str(output_dir / screenshot_name), full_page=True)
    except Exception:
        screenshot_name = ""

    result: dict[str, Any] = {
        "viewport": {"width": width, "height": height},
        "response_status": response_status,
        "load_seconds": round(load_seconds, 4),
        "navigation_error": navigation_error,
        "console_errors": console_errors[-20:],
        "page_errors": page_errors[-20:],
        "screenshot": screenshot_name,
        "storage": _storage_inventory(page),
        "navigation_timing": _navigation_timing(page),
        "controls": _control_styles(page),
    }
    context.close()
    return result


def _storage_fill_script(storage_fill_mb: float) -> str:
    target_bytes = int(storage_fill_mb * 1024 * 1024)
    return f"""
    (() => {{
      try {{
        const target = {target_bytes};
        const chunk = 'x'.repeat(64 * 1024);
        let used = 0;
        let index = 0;
        while (used < target) {{
          const key = `itinerary-qa-fill:${{index}}`;
          localStorage.setItem(key, chunk);
          used += key.length + chunk.length;
          index += 1;
        }}
      }} catch (_error) {{}}
    }})();
    """


def _storage_inventory(page: Any) -> dict[str, Any]:
    try:
        return page.evaluate(
            """
            () => {
              try {
                const encoder = new TextEncoder();
                const entries = [];
                let totalBytes = 0;
                for (let index = 0; index < localStorage.length; index += 1) {
                  const key = localStorage.key(index);
                  if (!key) continue;
                  const value = localStorage.getItem(key) || '';
                  const bytes = encoder.encode(key).length + encoder.encode(value).length;
                  totalBytes += bytes;
                  entries.push({key, bytes});
                }
                entries.sort((a, b) => b.bytes - a.bytes || a.key.localeCompare(b.key));
                return {ok: true, total_bytes: totalBytes, entries};
              } catch (error) {
                return {ok: false, error_type: error?.name || 'Error', entries: []};
              }
            }
            """
        )
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__, "entries": []}


def _navigation_timing(page: Any) -> dict[str, Any]:
    try:
        return page.evaluate(
            """
            () => {
              const entry = performance.getEntriesByType('navigation')[0];
              if (!entry) return {};
              return {
                response_end_ms: Math.round(entry.responseEnd * 100) / 100,
                dom_content_loaded_ms: Math.round(entry.domContentLoadedEventEnd * 100) / 100,
                load_event_ms: Math.round(entry.loadEventEnd * 100) / 100,
                transfer_size: entry.transferSize || 0,
                decoded_body_size: entry.decodedBodySize || 0,
              };
            }
            """
        )
    except Exception:
        return {}


def _control_styles(page: Any) -> dict[str, Any]:
    controls = {
        "first_text_input": 'div[data-testid="stTextInput"] input',
        "primary_button": 'button[kind="primary"]',
    }
    result: dict[str, Any] = {}
    for name, selector in controls.items():
        result[name] = _computed_style(page, selector)
    try:
        open_button = page.get_by_role("button", name="Open project")
        if open_button.count():
            open_button.first.click(timeout=5_000)
            page.wait_for_timeout(500)
            result["project_search"] = _computed_style(
                page,
                'input[placeholder="Name or folder/reference…"], input[placeholder="Name, folder or reference"]',
            )
            result["project_apply"] = _computed_style_by_text(page, "Apply")
    except Exception as exc:
        result["project_explorer_error"] = type(exc).__name__
    return result


def _computed_style(page: Any, selector: str) -> dict[str, Any]:
    try:
        return page.eval_on_selector(
            selector,
            """
            element => {
              const style = getComputedStyle(element);
              return {
                tag: element.tagName,
                placeholder: element.getAttribute('placeholder') || '',
                color: style.color,
                background_color: style.backgroundColor,
                border_top: style.borderTop,
                border_right: style.borderRight,
                border_bottom: style.borderBottom,
                border_left: style.borderLeft,
                opacity: style.opacity,
                visibility: style.visibility,
              };
            }
            """,
        )
    except Exception:
        return {"found": False}


def _computed_style_by_text(page: Any, text: str) -> dict[str, Any]:
    try:
        locator = page.get_by_role("button", name=text, exact=True)
        if not locator.count():
            return {"found": False}
        return locator.first.evaluate(
            """
            element => {
              const style = getComputedStyle(element);
              return {
                found: true,
                color: style.color,
                background_color: style.backgroundColor,
                border: style.border,
                opacity: style.opacity,
              };
            }
            """
        )
    except Exception:
        return {"found": False}


if __name__ == "__main__":
    raise SystemExit(main())
