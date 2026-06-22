from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/render.js",
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
