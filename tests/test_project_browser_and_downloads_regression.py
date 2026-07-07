from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text


def test_calculator_no_longer_auto_clicks_browser_downloads() -> None:
    action_source = read_contract_text("app_modules/calculator_download_action.py")
    render_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_render.js")
    page_source = read_contract_text("app_modules/calculator_page.py")

    assert "prepare_staged_calculation_download" in action_source
    assert "render_ready_calculation_download" in action_source
    assert "base64" not in action_source
    assert "link.click()" not in render_source
    assert "triggerPendingDownload" not in render_source
    assert "pending_download=None" in page_source
    assert "Download prepared Excel" in action_source


def test_open_project_browser_has_search_delete_files_and_inline_contrast_css() -> None:
    ui_source = read_contract_text("app_modules/project_browser_ui.py")
    from ui import style_app_shell

    css = style_app_shell.CSS

    assert "Search projects" in ui_source
    assert "Delete permanently" in ui_source
    assert "Prepare calculator file" in ui_source
    assert "Download calculator file" in ui_source
    assert "list_cloud_calculation_files" in ui_source
    assert "@st.dialog" not in ui_source
    assert "OPEN_PROJECT_BROWSER_VISIBLE_KEY" in ui_source
    assert ".open-project-workspace .open-project-copy strong" in css
    assert "background: #1f2630 !important;" in css
    assert "color: #fffdf8 !important;" in css
    assert '.open-project-workspace [data-testid="stFileUploaderDropzone"]' in css
