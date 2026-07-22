from __future__ import annotations

from tests.support.static_contracts import read_contract_text


def test_calculator_prepares_then_downloads_excel_from_the_grid_toolbar() -> None:
    action_source = read_contract_text("app_modules/calculator_download_action.py")
    actions_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_actions.js")
    excel_actions_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_excel_actions.js")
    toolbar_source = read_contract_text("calculator_grid_component/frontend/js/calculator_grid_toolbar_render.js")
    page_source = read_contract_text("app_modules/calculator_page.py")

    assert "prepare_staged_calculation_download" in action_source
    assert "ready_calculation_download_payload" in action_source
    assert '"content_base64"' in action_source
    assert '"content": export.content' not in action_source
    assert "saved_to_cloud" not in action_source
    assert "render_ready_calculation_download" not in action_source
    assert "auto_download" not in action_source
    assert "auto_download" not in actions_source
    assert "downloadPreparedExcel" in actions_source
    assert "anchor.click()" in excel_actions_source
    assert "pending_download=pending_download" in page_source
    assert "Excel ready" in toolbar_source


def test_open_project_manager_is_paged_compact_and_loads_files_only_for_selection() -> None:
    ui_source = read_contract_text("app_modules/project_browser_ui.py")
    list_source = read_contract_text("app_modules/project_browser_list_ui.py")
    detail_source = read_contract_text("app_modules/project_browser_detail_ui.py")
    calculator_file_source = read_contract_text("app_modules/project_browser_calculation_files.py")
    from ui import style_app_shell

    css = style_app_shell.CSS

    assert "Search projects" in ui_source
    assert "Sort" in ui_source
    assert "list_cloud_itinerary_page" in ui_source
    assert 'st.container(height=480, border=True, key="cloud_project_manager")' in ui_source
    assert "render_project_list(page)" in ui_source
    assert "render_selected_project_panel(selected)" in ui_source
    assert "render_calculation_files" not in list_source
    assert detail_source.count("render_calculation_files(project_id)") == 1
    assert "Delete permanently" in detail_source
    assert 'st.popover("…"' in list_source
    assert "Prepare calculator file" in calculator_file_source
    assert "Download calculator file" in calculator_file_source
    assert "Delete file permanently" in calculator_file_source
    assert "list_cloud_calculation_files" in calculator_file_source
    assert "@st.dialog" not in ui_source
    assert "OPEN_PROJECT_BROWSER_VISIBLE_KEY" in ui_source
    assert ".cloud-project-row" in css
    assert ".cloud-project-detail-card" in css
    assert "background: #1f2630 !important;" in css
    assert '.block-container:has(.open-project-workspace) [data-testid="stFileUploaderDropzone"]' in css
