from __future__ import annotations

from pathlib import Path


def test_calculator_no_longer_auto_clicks_browser_downloads() -> None:
    action_source = Path("app_modules/calculator_download_action.py").read_text(encoding="utf-8")
    render_source = Path("calculator_grid_component/frontend/js/calculator_grid_render.js").read_text(encoding="utf-8")
    page_source = Path("app_modules/calculator_page.py").read_text(encoding="utf-8")

    assert "prepare_staged_calculation_download" in action_source
    assert "render_ready_calculation_download" in action_source
    assert "base64" not in action_source
    assert "link.click()" not in render_source
    assert "triggerPendingDownload" not in render_source
    assert "pending_download=None" in page_source
    assert "Download prepared Excel" in action_source


def test_open_project_dialog_has_search_delete_files_and_contrast_css() -> None:
    ui_source = Path("app_modules/project_browser_ui.py").read_text(encoding="utf-8")
    from ui import style_app_shell

    css = style_app_shell.CSS

    assert "Search projects" in ui_source
    assert "Delete permanently" in ui_source
    assert "Prepare calculator file" in ui_source
    assert "Download calculator file" in ui_source
    assert "list_cloud_calculation_files" in ui_source
    assert "div[role=\"dialog\"] .open-project-copy strong" in css
    assert "color: #fffdf8 !important;" in css
    assert "div[role=\"dialog\"] [data-testid=\"stFileUploaderDropzone\"]" in css
