import json
import re
from pathlib import Path

from visual_editor_component.style_presets import (
    ALLOWED_STYLE_CLASSES,
    COLOR_STYLE_CLASSES,
    CONTROLLED_STYLE_CLASSES,
    FONT_FAMILY_STYLE_CLASSES,
    FONT_SIZE_STYLE_CLASSES,
    SPACING_STYLE_CLASSES,
    TEXT_STYLE_CLASSES,
    block_html,
    preset_class_map,
    style_preset_registry,
)


def _frontend_registry():
    js = Path("visual_editor_component/frontend/js/style_presets.js").read_text(encoding="utf-8")
    match = re.search(
        r"window\.CONTROLLED_EDITOR_STYLE_REGISTRY\s*=\s*(\{.*?\});\s*\n\nfunction",
        js,
        flags=re.DOTALL,
    )
    assert match, "frontend style registry assignment was not found"
    return json.loads(match.group(1))


def test_patch_bq_frontend_registry_matches_python_registry():
    assert _frontend_registry() == style_preset_registry()


def test_patch_bq_controlled_classes_have_single_registry_source():
    assert preset_class_map("text_styles")["heading"] == "ve-text-heading"
    assert preset_class_map("colors")["accent_gold"] == "ve-color-accent"
    assert preset_class_map("spacing")["compact"] == "ve-spacing-compact"
    assert preset_class_map("font_families")["georgia"] == "ve-font-georgia"
    assert preset_class_map("font_sizes")["size_12"] == "ve-size-12"
    assert "ve-note-block" in ALLOWED_STYLE_CLASSES
    assert "ve-divider" in ALLOWED_STYLE_CLASSES
    assert set(CONTROLLED_STYLE_CLASSES) == (
        set(TEXT_STYLE_CLASSES)
        | set(FONT_FAMILY_STYLE_CLASSES)
        | set(FONT_SIZE_STYLE_CLASSES)
        | set(COLOR_STYLE_CLASSES)
        | set(SPACING_STYLE_CLASSES)
    )


def test_patch_bq_frontend_uses_registry_for_toolbar_and_sanitizer():
    index_html = Path("visual_editor_component/frontend/index.html").read_text(encoding="utf-8")
    inspector_js = Path("visual_editor_component/frontend/js/editor_inspector.js").read_text(encoding="utf-8")
    text_tools_js = Path("visual_editor_component/frontend/js/editor_text_tools.js").read_text(encoding="utf-8")

    assert '<script src="js/style_presets.js"></script>' in index_html
    assert "controlledPresetOptionsHtml('font_families'" in inspector_js
    assert "controlledPresetOptionsHtml('font_sizes'" in inspector_js
    assert "controlledPresetOptionsHtml('text_styles'" in inspector_js
    assert "controlledPresetOptionsHtml('colors'" in inspector_js
    assert "controlledPresetClassMap('text_styles')" in text_tools_js
    assert "controlledEditorAllowedClasses()" in text_tools_js
    assert "controlledBlockTemplate('note')" in text_tools_js
    assert "controlledBlockTemplate('divider')" in text_tools_js


def test_patch_bq_pdf_uses_registry_for_controlled_classes():
    render_content = Path("pdf_exporter_modules/render_content.py").read_text(encoding="utf-8")

    assert "visual_editor_component.style_presets" in render_content
    assert "pdf_base_style_for_classes" in render_content
    assert "pdf_effects_for_classes" in render_content
    assert "ve-text-small-note" not in render_content
    assert "ve-color-accent" not in render_content


def test_patch_bq_block_templates_remain_controlled_html():
    note = block_html("note")
    divider = block_html("divider")

    assert "ve-note-block" in note
    assert "ve-text-small-note" in note
    assert "ve-color-muted" in note
    assert "style=" not in note
    assert "ve-divider-block" in divider
    assert "ve-divider" in divider
