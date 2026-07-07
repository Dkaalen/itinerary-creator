import json
import re
from pathlib import Path
from tests.support.static_contracts import read_contract_text

from visual_editor_component.style_presets import preset_class_map, preset_group


def _frontend_registry() -> dict:
    js = read_contract_text("visual_editor_component/frontend/js/style_preset_data.js")
    match = re.search(
        r"window\.CONTROLLED_EDITOR_STYLE_REGISTRY\s*=\s*(\{.*?\});",
        js,
        flags=re.DOTALL,
    )
    assert match, "frontend style registry assignment was not found"
    return json.loads(match.group(1))


def test_normal_export_flow_is_direct_and_not_a_readiness_dashboard():
    source = (
        read_contract_text("app_modules/export_step.py")
        + read_contract_text("app_modules/export_download_station.py")
    )

    assert "def _render_fatal_export_blockers" in source
    assert "Create PDF" in source
    assert "Download PDF" in source
    assert "def _render_export_readiness_panel" not in source
    assert "Export checks" not in source
    assert "export_readiness_panel_html(readiness)" in source
    assert "Project downloads" not in source
    assert "def _render_secondary_downloads" not in source
    assert "def _render_pdf_profile_selector" not in source
    assert "Download project JSON" not in source
    assert "Download HTML" not in source
    assert "HTML download" not in source
    assert "Proposal profile" not in source


def test_dm_sans_is_available_as_optional_editor_font_without_replacing_default():
    fonts = list(preset_group("font_families"))
    font_ids = [font.get("id") for font in fonts]
    dm_sans = next(font for font in fonts if font.get("id") == "dm_sans")
    frontend_fonts = _frontend_registry()["font_families"]
    css = read_contract_text("visual_editor_component/frontend/styles/editor_text_tools.css")

    assert font_ids[0] == "default"
    assert preset_class_map("font_families")["default"] == ""
    assert dm_sans["label"] == "DM Sans"
    assert dm_sans["class_name"] == "ve-font-dm-sans"
    assert dm_sans["pdf_font_name"] == "Helvetica"
    assert any(font.get("id") == "dm_sans" for font in frontend_fonts)
    assert ".ve-font-dm-sans" in css
    assert "'DM Sans'" in css


def test_normal_input_flow_exposes_project_file_open_and_keeps_legacy_loader_debug_only():
    source = read_contract_text("app_modules/input_step.py")
    project_browser_ui = read_contract_text("app_modules/project_browser_ui.py")

    assert "Generate agent itinerary" in source
    assert "Generate customer itinerary" in source
    assert "Supplier text" in source
    assert "render_open_project_file_action()" in source
    assert "Open uploaded backup" in project_browser_ui
    assert "Load legacy editable project JSON" in source
    assert source.index("if is_debug_mode(st.session_state):") < source.index("Load legacy editable project JSON")
