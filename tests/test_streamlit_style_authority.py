from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text

from ui import (
    style_app_chrome,
    style_app_shell,
    style_calculator,
    style_component_layout,
    style_input_workspace,
    style_project_browser,
    style_project_browser_detail,
    style_workspace_header,
)


STYLE_MODULES = (
    Path("ui/style_app_shell.py"),
    Path("ui/style_app_chrome.py"),
    Path("ui/style_workspace_header.py"),
    Path("ui/style_calculator.py"),
    Path("ui/style_component_layout.py"),
    Path("ui/style_input_workspace.py"),
    Path("ui/style_project_browser.py"),
    Path("ui/style_project_browser_detail.py"),
)


def test_streamlit_theme_keeps_native_tables_in_the_light_booknordics_shell() -> None:
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")

    assert 'base = "light"' in config
    assert 'primaryColor = "#1F3447"' in config
    assert 'backgroundColor = "#FBFAF7"' in config
    assert 'textColor = "#1F2630"' in config


def test_app_shell_is_composition_only_not_a_css_god_file() -> None:
    source = read_contract_text("ui/style_app_shell.py")

    assert len(source.splitlines()) <= 60
    assert "CSS = \"\".join" in source
    assert "data-testid" not in source
    assert ".cloud-project-card" not in source
    assert ".supplier-preview-panel" not in source


def test_streamlit_style_authority_is_split_by_surface() -> None:
    assert "html, body, [data-testid=\"stAppViewContainer\"]" in style_app_chrome.BASE_CSS
    assert ".studio-brand-link" in style_workspace_header.CSS
    assert ".supplier-preview-panel" in style_input_workspace.SUPPLIER_PREVIEW_CSS
    assert ".calculator-heading" in style_calculator.CALCULATOR_PAGE_CSS
    assert ".st-key-workflow_stage_actions" in style_component_layout.CSS
    assert "overflow-wrap: anywhere" in style_component_layout.CSS
    assert ".st-key-cloud_project_explorer" in style_project_browser.PROJECT_BROWSER_CSS
    assert "stDataFrame" in style_project_browser.PROJECT_BROWSER_CSS
    assert ".cloud-project-detail-card" in style_project_browser_detail.CSS
    assert "stVerticalBlockBorderWrapper" in style_project_browser.PROJECT_BROWSER_CSS


def test_composed_app_shell_preserves_all_split_sections_in_order() -> None:
    expected = "".join(
        (
            style_app_chrome.BASE_CSS,
            style_workspace_header.CSS,
            style_input_workspace.PAGE_LAYOUT_CSS,
            style_calculator.CSS,
            style_project_browser.PROJECT_COPY_CSS,
            style_app_chrome.STREAMLIT_COMPONENT_CSS,
            style_input_workspace.SUPPLIER_PREVIEW_CSS,
            style_project_browser.PROJECT_BROWSER_CSS,
            style_project_browser_detail.CSS,
        )
    )

    assert style_app_shell.CSS == expected


def test_focused_streamlit_style_modules_stay_small() -> None:
    line_counts = {path.as_posix(): len(path.read_text(encoding="utf-8").splitlines()) for path in STYLE_MODULES}

    assert line_counts["ui/style_app_shell.py"] <= 60
    assert all(lines <= 260 for path, lines in line_counts.items() if path != "ui/style_app_shell.py")
