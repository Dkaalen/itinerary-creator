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


def test_ui17_outline_page_cards_are_navigation_not_action_menus():
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    editing_js = Path("visual_editor_component/frontend/js/editing.js").read_text(encoding="utf-8")

    assert 'data-outline-page-id' in render_js
    assert 'class="outline-jump"' in render_js
    assert '<summary>Actions</summary>' not in render_js
    assert 'class="outline-action-menu"' not in render_js
    assert "event.target?.closest?.('[data-doc-page-action]')" in editing_js


def test_ui17_restores_inline_page_header_controls():
    source = _frontend_source()

    assert 'class="page-controls" aria-label="Page actions"' in source
    assert 'data-doc-page-action="add-after"' in source
    assert "addManualPageAfter" in source
    assert 'title="Move page up"' in source
    assert 'title="Move page down"' in source
    assert 'title="Hide this page from the itinerary"' in source
    assert '<summary>Page menu</summary>' not in source


def test_ui16_compacts_page_context_and_strengthens_selection_state():
    source = _frontend_source()

    assert "page-context-card" in source
    assert '<details class="inspector-card page-context-card' in source
    assert ".page-context-card:not([open])" in source
    assert ".selected-editor-block" in source
    assert 'content: "Selected"' in source
