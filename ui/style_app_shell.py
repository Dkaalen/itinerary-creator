"""Composed app-shell CSS facade kept for compatibility.

The actual style authority lives in the focused style modules imported here.
Keep this file as composition only; do not add raw selectors here.
"""

from ui import (
    style_app_chrome,
    style_calculator,
    style_input_workspace,
    style_project_browser,
    style_workspace_header,
)

CSS = "".join(
    (
        style_app_chrome.BASE_CSS,
        style_workspace_header.CSS,
        style_input_workspace.PAGE_LAYOUT_CSS,
        style_calculator.CSS,
        style_project_browser.PROJECT_COPY_CSS,
        style_app_chrome.STREAMLIT_COMPONENT_CSS,
        style_input_workspace.SUPPLIER_PREVIEW_CSS,
        style_project_browser.PROJECT_BROWSER_CSS,
    )
)
