from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "styles/editor_base.css",
            "styles/editor_inspector.css",
            "styles/editor_outline.css",
            "styles/editor_shell.css",
            "styles/editor_toolbar.css",
            "styles/editor_layout_tools.css",
            "styles/editor_canvas_workspace.css",
            "styles/editor_tokens.css",
            "js/render.js",
            "js/editor_dirty_state.js",
            "js/editor_text_tools.js",
            "js/editor_document_model.js",
            "js/editor_document_outline.js",
            "js/editor_inspector.js",
            "js/editor_inspector_text_panel.js",
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


def test_ui18_removes_duplicate_toolbar_formatting_shortcuts():
    source = _frontend_source()

    assert '<details class="quick-tools">' not in source
    assert '<summary>Quick formatting</summary>' not in source
    assert 'aria-label="Quick formatting shortcuts"' not in source
    assert 'Inspector is primary; these are shortcuts for the selected block.' not in source
    assert 'class="pages-menu"' in source
    assert '.pages-menu .document-outline' in source


def test_ui18_keeps_advanced_tools_debug_only_and_formatting_in_inspector():
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    debug_js = Path("visual_editor_component/frontend/js/editor_debug_shell.js").read_text(encoding="utf-8")
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
