"""Browser cascade harness for Streamlit-owned controls and keyed surfaces."""

from __future__ import annotations

import shutil
from typing import Any

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

from ui import (
    style_component_layout,
    style_forms,
    style_input_workspace,
    style_project_browser,
    style_project_browser_detail,
    style_tokens,
)


def rendered_style_fixture_html() -> str:
    """Return a small DOM using Streamlit 1.45 test IDs and BaseWeb shells."""

    css = "\n".join(
        (
            style_tokens.CSS,
            style_forms.CSS,
            style_component_layout.CSS,
            style_input_workspace.PAGE_LAYOUT_CSS,
            style_project_browser.PROJECT_COPY_CSS,
            style_project_browser.PROJECT_BROWSER_CSS,
            style_project_browser_detail.CSS,
        )
    )
    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          html, body {{ margin: 0; background: #f8f6f1; font-family: Inter, sans-serif; }}
          .block-container {{ width: min(calc(100% - 2rem), 1180px); margin: 0 auto; padding: 1rem 0; }}
          [data-testid="stHorizontalBlock"] {{ display: flex; gap: .75rem; }}
          [data-testid="column"] {{ flex: 1 1 0; min-width: 0; }}
          [data-testid="stVerticalBlock"] {{ display: grid; gap: .55rem; }}
          label p {{ margin: 0 0 .25rem; }}
          {css}
        </style>
      </head>
      <body>
        <main data-testid="stAppViewContainer">
          <div class="block-container">
            <section class="st-key-input_workspace_form" data-surface="itinerary">
              <div data-testid="stTextInput">
                <label><p>Itinerary name</p></label>
                <div data-baseweb="input">
                  <div data-baseweb="base-input">
                    <input id="itinerary-name" placeholder="Itinerary name" />
                  </div>
                </div>
              </div>
            </section>

            <section class="st-key-project_explorer_workspace" data-surface="explorer">
              <div class="st-key-project_explorer_header">
                <div data-testid="stHorizontalBlock">
                  <div data-testid="column"><div class="project-explorer-heading"><span class="project-explorer-folder">▰</span><div><strong>Project Explorer</strong><span>Find and organize saved itineraries.</span></div></div></div>
                  <div data-testid="column"><div data-testid="stButton"><button kind="secondary"><p>Close</p></button></div></div>
                </div>
              </div>
              <div class="st-key-cloud_project_explorer">
                <div class="st-key-project_explorer_filter_form">
                  <form data-testid="stForm">
                    <div class="st-key-project_explorer_filter_fields">
                      <div data-testid="stHorizontalBlock">
                        <div data-testid="column">
                          <div data-testid="stTextInput">
                            <label><p>Search projects</p></label>
                            <div data-baseweb="input">
                              <div data-baseweb="base-input">
                                <input id="project-search" placeholder="Name, folder or reference" />
                              </div>
                            </div>
                          </div>
                        </div>
                        <div data-testid="column">
                          <div data-testid="stSelectbox">
                            <label><p>Sort</p></label>
                            <div data-baseweb="select"><div><span>Recently saved</span></div></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="st-key-project_explorer_filter_actions">
                      <div data-testid="stHorizontalBlock">
                        <div data-testid="column"><div data-testid="stFormSubmitButton"><button id="apply-project-filter" kind="primary" data-testid="baseButton-primary"><p>Apply</p></button></div></div>
                        <div data-testid="column"><div data-testid="stFormSubmitButton"><button kind="secondary" data-testid="baseButton-secondary"><p>Reset</p></button></div></div>
                        <div data-testid="column"></div>
                      </div>
                    </div>
                  </form>
                </div>
                <div class="st-key-project_explorer_selected_actions">
                  <div data-testid="stHorizontalBlock">
                    <div data-testid="column"><div data-testid="stButton"><button kind="primary" disabled data-testid="baseButton-primary"><p>Project is open</p></button></div></div>
                    <div data-testid="column"><div data-testid="stButton"><button kind="secondary"><p>Rename</p></button></div></div>
                    <div data-testid="column"><div data-testid="stButton"><button kind="secondary"><p>Save as copy</p></button></div></div>
                    <div data-testid="column"><div class="st-key-delete_selected_cloud_project_demo"><div data-testid="stButton"><button kind="secondary"><p>Delete</p></button></div></div></div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>
      </body>
    </html>
    """


def open_rendered_style_page(*, width: int = 1440, height: int = 1000):
    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    if not executable:
        pytest.skip("Chromium is unavailable.")
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": width, "height": height})
    page.set_content(rendered_style_fixture_html(), wait_until="load")
    return manager, browser, page


def computed_style(page: Any, selector: str) -> dict[str, str]:
    return page.locator(selector).evaluate(
        """
        element => {
          const style = getComputedStyle(element);
          return {
            color: style.color,
            backgroundColor: style.backgroundColor,
            borderTopColor: style.borderTopColor,
            borderBottomColor: style.borderBottomColor,
            borderTopWidth: style.borderTopWidth,
            borderBottomWidth: style.borderBottomWidth,
            boxShadow: style.boxShadow,
            outline: style.outline,
            opacity: style.opacity,
          };
        }
        """
    )
