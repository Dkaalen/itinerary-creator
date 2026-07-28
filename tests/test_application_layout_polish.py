from __future__ import annotations

from pathlib import Path

from ui import style_component_layout, style_export, style_forms, style_input_workspace


def _text(relative_path: str) -> str:
    return Path(relative_path).read_text(encoding="utf-8")


def test_general_textareas_are_compact_but_supplier_input_keeps_working_height() -> None:
    assert "min-height: 8rem !important;" in style_forms.CSS
    assert "min-height: 330px !important;" not in style_forms.CSS
    assert '.st-key-input_workspace_form div[data-testid="stTextArea"] textarea' in style_input_workspace.PAGE_LAYOUT_CSS
    assert "min-height: 280px !important;" in style_input_workspace.PAGE_LAYOUT_CSS
    assert "min-height: 240px !important;" in style_input_workspace.PAGE_LAYOUT_CSS


def test_controls_use_workspace_typography_instead_of_serif_form_fields() -> None:
    input_rules = style_forms.CSS.split('div[data-testid="stTextInput"] input,', 1)[1]

    assert "font-family: inherit !important;" in input_rules
    assert 'font-family: Georgia, "Times New Roman", serif !important;' not in input_rules
    assert "min-height: 3rem !important;" in input_rules


def test_shared_layout_contract_keeps_labels_inside_controls() -> None:
    css = style_component_layout.CSS

    assert "overflow-wrap: anywhere !important;" in css
    assert "white-space: normal !important;" in css
    assert "min-width: 0 !important;" in css
    assert "text-overflow: ellipsis !important;" in css
    assert '@media (max-width: 520px)' in css
    assert "flex-basis: 100% !important;" in css


def test_owned_workflow_surfaces_have_responsive_container_keys() -> None:
    expected = {
        "app_modules/input_step.py": ("input_top_actions", "input_generation_actions"),
        "app_modules/app_header.py": ("workflow_stage_actions",),
        "app_modules/project_save_ui.py": ("save_project_actions", "save_as_project_actions"),
        "app_modules/calculator_page.py": ("calculator_topbar",),
        "app_modules/local_library_page.py": ("local_library_topbar",),
        "app_modules/local_library_browser_ui.py": ("local_library_filters", "local_library_paging"),
        "app_modules/calculator_currency_controls.py": ("calculator_currency_editor",),
        "app_modules/local_library_status_ui.py": ("local_library_metrics",),
        "app_modules/add_pictures_cta.py": ("workflow_transaction_actions_add_pictures",),
        "app_modules/picture_pdf_cta.py": ("workflow_transaction_actions_picture_pdf",),
        "app_modules/export_step.py": ("workflow_transaction_actions_export_pdf",),
    }

    for relative_path, keys in expected.items():
        source = _text(relative_path)
        for key in keys:
            assert f'key="{key}"' in source


def test_long_timeout_actions_get_the_wide_center_column() -> None:
    for relative_path in (
        "app_modules/add_pictures_cta.py",
        "app_modules/picture_pdf_cta.py",
        "app_modules/export_step.py",
    ):
        source = _text(relative_path)
        assert "st.columns([0.22, 0.56, 0.22], gap=\"small\")" in source


def test_sticky_download_style_is_scoped_to_the_pdf_station() -> None:
    source = _text("app_modules/export_download_station.py")

    assert 'key=f"pdf_download_station_{location}"' in source
    assert 'div[class*="st-key-pdf_download_station_"]' in style_export.CSS
    assert '\ndiv[data-testid="stDownloadButton"]:has' not in style_export.CSS


def test_global_style_composition_includes_responsive_component_layout() -> None:
    source = _text("ui/styles.py")

    assert "style_component_layout" in source
    assert "style_forms.CSS,\n    style_component_layout.CSS," in source


def test_pdf_ready_panel_stacks_before_its_location_chip_can_overflow() -> None:
    assert ".export-readiness-panel,\n    .pdf-ready-panel" in style_export.CSS
    assert ".pdf-ready-panel .pdf-ready-location" in style_export.CSS
    assert "overflow-wrap: anywhere;" in style_export.CSS


def test_calculator_back_action_can_fill_its_owned_topbar_column() -> None:
    navigation = _text("app_modules/calculator_navigation.py")
    calculator_page = _text("app_modules/calculator_page.py")

    assert "def render_back_to_main_page_button(*, use_container_width: bool = False)" in navigation
    assert "use_container_width=use_container_width" in navigation
    assert '"Back to itinerary"' in calculator_page
    assert "close_calculator_page(st.session_state)" in calculator_page
