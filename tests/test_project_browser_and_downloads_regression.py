from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text


def test_calculator_prepares_then_downloads_excel_from_the_grid_toolbar() -> None:
    action_source = read_contract_text("app_modules/calculator_download_action.py")
    actions_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_actions.js")
    render_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_render.js")
    page_source = read_contract_text("app_modules/calculator_page.py")

    assert "prepare_staged_calculation_download" in action_source
    assert "ready_calculation_download_payload" in action_source
    assert '"content_base64"' in action_source
    assert "downloadPreparedExcel" in actions_source
    assert "anchor.click()" in actions_source
    assert "pending_download=pending_download" in page_source
    assert "Excel ready" in render_source


def test_open_project_browser_has_search_delete_files_and_inline_contrast_css() -> None:
    ui_source = read_contract_text("app_modules/project_browser_ui.py")
    calculator_file_source = read_contract_text("app_modules/project_browser_calculation_files.py")
    from ui import style_app_shell

    css = style_app_shell.CSS

    assert "Search projects" in ui_source
    assert "Delete permanently" in ui_source
    assert "render_calculation_files" in ui_source
    assert "Prepare calculator file" in calculator_file_source
    assert "Download calculator file" in calculator_file_source
    assert "Delete file permanently" in calculator_file_source
    assert "list_cloud_calculation_files" in calculator_file_source
    assert "@st.dialog" not in ui_source
    assert "OPEN_PROJECT_BROWSER_VISIBLE_KEY" in ui_source
    assert ".open-project-workspace .open-project-copy strong" in css
    assert "background: #1f2630 !important;" in css
    assert "color: #fffdf8 !important;" in css
    assert '.block-container:has(.open-project-workspace) [data-testid="stFileUploaderDropzone"]' in css
