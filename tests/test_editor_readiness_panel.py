from pathlib import Path
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_pdf_readiness_panel_surfaces_export_confidence_signals():
    source = _frontend_source()

    assert "pdfReadinessStatus" in source
    assert "pdfReadinessPanelHtml" in source
    assert "pdfReadinessBadgeHtml" in source
    assert "Export checks" in source
    assert "editorDebugReviewHtml" in source
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
    assert "Open day page" in source
    assert "selectedPageValidationHtml" in source
    assert "validation-card" in source
    assert "No warnings linked to the selected page" in source
