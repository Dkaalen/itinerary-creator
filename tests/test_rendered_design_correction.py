from __future__ import annotations

from pathlib import Path

from ui import (
    style_app_chrome,
    style_calculator,
    style_forms,
    style_input_workspace,
    style_project_browser,
    style_project_browser_detail,
)


def _relative_luminance(hex_color: str) -> float:
    values = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_relative_luminance(foreground), _relative_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_action_colors_have_readable_contrast() -> None:
    assert _contrast("#ffffff", "#233446") >= 4.5
    assert _contrast("#65625c", "#e7e4dd") >= 4.5
    assert _contrast("#7b342e", "#fff5f3") >= 4.5


def test_disabled_primary_controls_cannot_keep_dark_text_or_dark_fill() -> None:
    css = style_forms.CSS
    assert 'button[data-testid="baseButton-primary"]:disabled' in css
    assert "background: #e7e4dd !important;" in css
    assert "color: #65625c !important;" in css
    assert "button[disabled] *" in css


def test_workspace_is_not_wrapped_in_the_retired_decorative_card() -> None:
    css = style_app_chrome.BASE_CSS
    assert "box-shadow: none !important;" in css
    assert "content: none !important;" in css
    assert "border-radius: 0 !important;" in css


def test_input_explorer_and_calculator_use_compact_owned_layouts() -> None:
    assert "min-height: 280px !important;" in style_input_workspace.PAGE_LAYOUT_CSS
    assert ".st-key-cloud_project_explorer" in style_project_browser.PROJECT_BROWSER_CSS
    assert ".cloud-project-selected-strip" in style_project_browser_detail.CSS
    assert ".st-key-calculator_setup_bar" in style_calculator.CALCULATOR_PAGE_CSS


def test_calculator_common_toolbar_is_visible_and_less_used_tools_are_grouped() -> None:
    source = Path("calculator_grid_component/frontend/js/calculator_grid_toolbar_render.js").read_text(encoding="utf-8")
    css = Path("calculator_grid_component/frontend/styles/calculator_grid.css").read_text(encoding="utf-8")
    assert "Files and output" in source
    assert "Rows" in source
    assert "Edit" in source
    assert '<details class="calculator-toolbar-more">' in source
    assert "More tools" in source
    assert "@media (max-width: 900px)" in css
    assert ".calculator-toolbar-more" in css


def test_surface_styles_use_keyed_ownership_instead_of_page_heading_detection() -> None:
    input_css = style_input_workspace.PAGE_LAYOUT_CSS
    project_css = style_project_browser.PROJECT_BROWSER_CSS

    assert ".st-key-input_workspace_form" in input_css
    assert ".st-key-local_library_workspace" in input_css
    assert ".block-container:has(.input-page-heading)" not in input_css
    assert ".block-container:has(.local-library-heading)" not in input_css
    assert ".st-key-project_explorer_workspace" in project_css
    assert ".st-key-project_explorer_filter_fields" in project_css
    assert ".st-key-project_explorer_bulk_actions" in project_css
    assert ".block-container:has(.project-explorer-heading)" not in project_css
    assert '.st-key-cloud_project_explorer [data-testid="stHorizontalBlock"]' not in project_css


def test_shared_form_owner_paints_baseweb_shell_not_inner_input() -> None:
    css = style_forms.CSS

    assert 'div[data-testid="stTextInput"] [data-baseweb="input"]' in css
    assert 'div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within' in css
    assert 'div[data-testid="stTextInput"] input' in css
    assert "border: 0 !important;" in css
    assert "background: transparent !important;" in css
    assert '[data-baseweb="input"],\n[data-baseweb="textarea"]' not in css


def test_project_explorer_copy_and_rows_have_explicit_owners() -> None:
    controls = Path("app_modules/project_browser_controls.py").read_text(encoding="utf-8")
    ui_source = Path("app_modules/project_browser_ui.py").read_text(encoding="utf-8")
    bulk_source = Path("app_modules/project_browser_bulk_ui.py").read_text(encoding="utf-8")
    detail_source = Path("app_modules/project_browser_detail_ui.py").read_text(encoding="utf-8")

    assert 'placeholder="Name, folder or reference"' in controls
    assert "Name or folder/reference" not in controls
    for key in (
        "project_explorer_workspace",
        "project_explorer_header",
        "project_explorer_backup",
        "project_explorer_backup_confirmation",
    ):
        assert f'key="{key}"' in ui_source
    for key in ("project_explorer_filter_fields", "project_explorer_filter_actions"):
        assert f'key="{key}"' in controls
    for key in ("project_explorer_bulk_actions", "project_explorer_delete_confirmation"):
        assert f'key="{key}"' in bulk_source
    for key in ("project_explorer_selected_actions", "project_explorer_open_confirmation"):
        assert f'key="{key}"' in detail_source
