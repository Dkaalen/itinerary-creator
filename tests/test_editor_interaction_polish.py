from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/render.js",
            "js/editing.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
        )
    )


def test_ui16_collapses_document_status_metrics_by_default():
    source = _frontend_source()

    assert 'class="studio-status-panel"' in source
    assert "Document status" in source
    assert "studio-status-panel:not([open]) .studio-status-strip" in source
    assert "studioDirtyPagesMetric" in source
    assert "studioSelectionMetric" in source
    assert "studioEditsMetric" in source


def test_ui16_moves_outline_page_actions_into_compact_menu():
    source = _frontend_source()

    assert 'class="outline-actions"' in source
    assert 'class="outline-action-menu"' in source
    assert '<summary>Actions</summary>' in source
    assert "event.target?.closest?.('[data-doc-page-action], .outline-actions, .outline-drag-handle')" in source
    assert 'data-doc-page-action="hide"' in source
    assert 'data-doc-page-action="duplicate"' in source


def test_ui16_collapses_page_header_controls_into_page_menu():
    source = _frontend_source()

    assert 'class="page-controls"' in source
    assert '<summary>Page menu</summary>' in source
    assert 'class="page-action-menu"' in source
    assert "Select page" in source
    assert "Move up" in source
    assert "Move down" in source
    assert "Delete page" in source


def test_ui16_compacts_page_context_and_strengthens_selection_state():
    source = _frontend_source()

    assert "page-context-card" in source
    assert '<details class="inspector-card page-context-card' in source
    assert ".page-context-card:not([open])" in source
    assert ".selected-editor-block" in source
    assert 'content: "Selected"' in source
