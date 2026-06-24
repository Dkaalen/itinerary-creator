from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    js_source = "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "js/render.js",
            "js/editing.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
            "js/editor_page_event_handlers.js",
        )
    )
    return read_resolved_frontend_css() + "\n" + js_source


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
    editing_js = "\n".join(
        Path("visual_editor_component/frontend/js", relative).read_text(encoding="utf-8")
        for relative in ("editing.js", "editor_page_event_handlers.js")
    )

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


def test_ui19_removes_sidebar_metadata_bloat_and_uses_non_jitter_selection():
    source = _frontend_source()
    render_right = source[source.index("function renderRightInspector"):]

    assert "page-context-card" in source
    assert '<details class="inspector-card page-context-card' not in render_right
    assert ".right-inspector .page-context-card" in source
    assert ".selected-editor-block" in source
    assert "content: none !important" in source


def test_ui20_preserves_canvas_selection_when_using_formatting_controls():
    frontend = Path("visual_editor_component/frontend")
    source = "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "js/state.js",
            "js/editor_text_tools.js",
            "js/editor_inspector.js",
            "js/editing.js",
        )
    )

    assert "savedCanvasSelectionRange" in source
    assert "rememberCanvasSelection" in source
    assert "restoreCanvasSelection" in source
    assert "selectionchange" in source
    assert "mousedown', rememberCanvasSelection" in source


def test_ui20_does_not_refresh_inspector_for_unchanged_selection():
    source = Path("visual_editor_component/frontend/js/editor_document_model.js").read_text(encoding="utf-8")

    assert "const changed = activePageId !== nextPageId" in source
    assert "if (changed) updateRightInspector();" in source
