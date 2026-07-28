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
