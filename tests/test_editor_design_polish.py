from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/render.js",
            "js/editor_dirty_state.js",
            "js/editor_text_tools.js",
            "js/editor_document_model.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
            "js/editor_warnings.js",
            "js/commands.js",
        )
    )


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


def test_ui14_collapses_duplicate_toolbar_shortcuts_behind_quick_formatting_panel():
    source = _frontend_source()

    assert '<details class="quick-tools">' in source
    assert '<summary>Quick formatting</summary>' in source
    assert 'aria-label="Quick formatting shortcuts"' in source
    assert 'Inspector is primary; these are shortcuts for the selected block.' in source
    assert 'Shortcut for the Inspector text style tool' in source
    assert 'Shortcut for Inspector → Add note' in source
    assert '.quick-tools summary' in source
    assert '.toolbar-hint' in source


def test_ui14_keeps_quick_formatting_separate_from_advanced_tools():
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")

    quick_position = render_js.index('class="quick-tools"')
    style_tools_position = render_js.index('class="toolbar-tools style-tools"')
    advanced_position = render_js.index('class="advanced-tools"')
    assert quick_position < style_tools_position < advanced_position
    assert 'id="textStylePreset"' in render_js
    assert 'id="colorPreset"' in render_js
    assert 'id="compactSpacingBtn"' in render_js
    assert 'id="normalSpacingBtn"' in render_js
