from __future__ import annotations

import re
from pathlib import Path

from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def _asset_text(relative: str) -> str:
    return Path("visual_editor_component/frontend", relative).read_text(encoding="utf-8")


def _asset_contains(relative: str, token: str) -> bool:
    return token in _asset_text(relative)


def _asset_omits(relative: str, token: str) -> bool:
    return token not in _asset_text(relative)


def test_ui16_collapses_document_status_metrics_by_default():
    source = _frontend_source()
    css_selectors = set(re.findall(r"([^{}]+)\{", source))

    assert 'class="studio-status-panel"' in source
    assert "Document status" in source
    assert any("studio-status-panel:not([open]) .studio-status-strip" in selector for selector in css_selectors)
    assert {"studioDirtyPagesMetric", "studioSelectionMetric", "studioEditsMetric"}.issubset(set(re.findall(r"id=\"([^\"]+)\"", source)))


def test_ui17_outline_page_cards_are_navigation_not_action_menus():
    outline_js = _asset_text("js/editor_document_outline.js")
    editing_js = _asset_text("js/editing.js") + _asset_text("js/editor_page_event_handlers.js")

    assert _asset_contains("js/editor_document_outline.js", "data-outline-page-id")
    assert _asset_contains("js/editor_document_outline.js", 'class="outline-jump"')
    assert _asset_omits("js/editor_document_outline.js", "<summary>Actions</summary>")
    assert _asset_omits("js/editor_document_outline.js", 'class="outline-action-menu"')
    assert "event.target?.closest?.('[data-doc-page-action]')" in editing_js


def test_ui17_restores_inline_page_header_controls():
    source = _frontend_source()
    page_actions = set(re.findall(r'data-doc-page-action="([^"]+)"', source))
    page_titles = set(re.findall(r'title="([^"]+)"', source))

    assert 'class="page-controls" aria-label="Page actions"' in source
    assert "add-after" in page_actions
    assert "addManualPageAfter" in source
    assert {"Move page up", "Move page down", "Hide this page from the itinerary"}.issubset(page_titles)
    assert "<summary>Page menu</summary>" not in source


def test_ui19_removes_sidebar_metadata_bloat_and_uses_non_jitter_selection():
    source = _frontend_source()
    render_right = source[source.index("function renderRightInspector") :]

    assert "page-context-card" in source
    assert '<details class="inspector-card page-context-card' not in render_right
    assert ".right-inspector .page-context-card" in source
    assert ".selected-editor-block" in source
    assert "content: none !important" in source


def test_ui20_preserves_canvas_selection_when_using_formatting_controls():
    source = "\n".join(
        _asset_text(relative)
        for relative in (
            "js/state.js",
            "js/editor_text_tools.js",
            "js/editor_text_selection.js",
            "js/editor_text_formatting.js",
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
    assert _asset_contains("js/editor_selection_model.js", "const changed = activePageId !== nextPageId")
    assert _asset_contains("js/editor_selection_model.js", "if (changed) updateRightInspector();")
