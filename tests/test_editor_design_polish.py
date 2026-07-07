from pathlib import Path
from tests.support.static_contracts import read_contract_text
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_editor_design_polish_adds_studio_status_strip():
    source = _frontend_source()

    assert "editorStudioStats" in source
    assert "studioStatusStripHtml" in source
    assert "studio-status-strip" in source
    assert "studio-metric" in source
    assert "Visible pages" in source
    assert "Manual pages" in source
    assert "Unsaved edits" in source
    assert "studioEditsMetric" in source
    assert "studioSelectionMetric" in source


def test_editor_design_polish_keeps_professional_panel_and_focus_styles():
    source = _frontend_source()

    assert "--shadow-panel" in source
    assert "--surface" in source
    assert ".toolbar-main" in source
    assert "button:focus-visible" in source
    assert "button:hover:not(:disabled)" in source
    assert ".outline-row:hover" in source
    assert ".document-outline::-webkit-scrollbar" in source
    assert "grid-template-columns: minmax(220px, 260px)" in source


def test_ui18_removes_duplicate_toolbar_formatting_shortcuts():
    source = _frontend_source()

    assert '<details class="quick-tools">' not in source
    assert '<summary>Quick formatting</summary>' not in source
    assert 'aria-label="Quick formatting shortcuts"' not in source
    assert 'Inspector is primary; these are shortcuts for the selected block.' not in source
    assert 'class="pages-menu"' in source
    assert '.pages-menu .document-outline' in source


def test_ui18_keeps_advanced_tools_debug_only_and_formatting_in_inspector():
    render_js = read_contract_text("visual_editor_component/frontend/js/render.js")
    debug_js = read_contract_text("visual_editor_component/frontend/js/editor_debug_shell.js")
    inspector_js = "\n".join(
        Path("visual_editor_component/frontend/js", name).read_text(encoding="utf-8")
        for name in ("editor_inspector.js", "editor_inspector_text_panel.js")
    )

    assert 'class="advanced-tools"' not in render_js
    assert 'class="advanced-tools"' in debug_js
    assert 'id="inspectorFontFamilyPreset"' in inspector_js
    assert 'id="inspectorFontSizePreset"' in inspector_js
    assert 'id="inspectorColorPreset"' in inspector_js
    assert 'id="textStylePreset"' not in render_js
    assert 'id="colorPreset"' not in render_js
