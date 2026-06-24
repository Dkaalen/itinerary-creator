import json
import re
from pathlib import Path

from visual_editor_component.style_presets import preset_class_map, preset_group


def _frontend_registry() -> dict:
    js = Path("visual_editor_component/frontend/js/style_presets.js").read_text(encoding="utf-8")
    match = re.search(
        r"window\.CONTROLLED_EDITOR_STYLE_REGISTRY\s*=\s*(\{.*?\});\s*\n\nfunction",
        js,
        flags=re.DOTALL,
    )
    assert match, "frontend style registry assignment was not found"
    return json.loads(match.group(1))


def test_normal_export_flow_is_direct_and_not_a_readiness_dashboard():
    source = Path("app_modules/export_step.py").read_text(encoding="utf-8")

    assert "def _render_fatal_export_blockers" in source
    assert "Create PDF" in source
    assert "Download PDF" in source
    assert "def _render_export_readiness_panel" not in source
    assert "Export checks" not in source
    assert "export-readiness-panel" not in source
    assert "Project downloads" not in source
    assert "Proposal profile" not in source[source.index("def render_export_step") :]


def test_dm_sans_is_available_as_optional_editor_font_without_replacing_default():
    fonts = list(preset_group("font_families"))
    font_ids = [font.get("id") for font in fonts]
    dm_sans = next(font for font in fonts if font.get("id") == "dm_sans")
    frontend_fonts = _frontend_registry()["font_families"]
    css = Path("visual_editor_component/frontend/styles/editor_text_presets.css").read_text(encoding="utf-8")

    assert font_ids[0] == "default"
    assert preset_class_map("font_families")["default"] == ""
    assert dm_sans["label"] == "DM Sans"
    assert dm_sans["class_name"] == "ve-font-dm-sans"
    assert dm_sans["pdf_font_name"] == "Helvetica"
    assert any(font.get("id") == "dm_sans" for font in frontend_fonts)
    assert ".ve-font-dm-sans" in css
    assert "'DM Sans'" in css
