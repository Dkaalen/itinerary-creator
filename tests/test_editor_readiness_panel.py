from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/state.js",
            "js/images.js",
            "js/render.js",
            "js/editor_dirty_state.js",
            "js/editor_text_tools.js",
            "js/editor_document_model.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
            "js/editor_warnings.js",
            "js/commands.js",
            "js/editing.js",
        )
    )


def test_pdf_readiness_panel_surfaces_export_confidence_signals():
    source = _frontend_source()

    assert "pdfReadinessStatus" in source
    assert "pdfReadinessPanelHtml" in source
    assert "pdfReadinessBadgeHtml" in source
    assert "PDF readiness" in source
    assert "unsaved_edits" in source
    assert "hiddenPageIssues" in source
    assert "pendingImagePreviewIssues" in source
    assert "editorImageWarnings" in source
    assert "flagged_issue" in source
    assert "pdf-readiness-panel" in source


def test_warnings_are_actionable_from_toolbar_and_inspector():
    source = _frontend_source()

    assert "warningTargetPageId" in source
    assert "data-warning-page-id" in source
    assert "data-readiness-page-id" in source
    assert "Review page" in source
    assert "selectedPageValidationHtml" in source
    assert "validation-card" in source
    assert "No warnings linked to the selected page" in source
