from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/render.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
        )
    )


def test_ui15_collapses_warning_and_readiness_noise_into_review_center():
    source = _frontend_source()

    assert "reviewCenterHtml" in source
    assert 'class="review-center"' in source
    assert "Review center" in source
    assert "review-center-grid" in source
    assert 'class="warning-panel"><summary>' in source
    assert 'class="pdf-readiness-panel ${escAttr(status.level)}"><summary>' in source
    assert "${reviewCenterHtml()}" in source


def test_ui17_protects_preview_canvas_from_sidebars():
    source = _frontend_source()

    assert "grid-template-columns: 184px minmax(var(--page-w), var(--page-w)) 240px" in source
    assert "max-width: 1246px" in source
    assert ".page-stack .page-wrap" in source
    assert "width: var(--page-w)" in source
    assert "overflow-x: auto" in source
    assert "justify-content: center" in source


def test_ui17_keeps_sidebars_sticky_without_overlaying_page_canvas():
    source = _frontend_source()

    assert ".document-outline," in source
    assert ".right-inspector" in source
    assert "position: sticky !important" in source
    assert "top: 112px" in source
    assert "max-height: calc(100vh - 126px)" in source
    assert "overflow-y: auto" in source
    assert "align-self: start" in source


def test_ui17_left_outline_is_clean_navigation_only():
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")

    assert 'class="outline-jump"' in render_js
    assert 'class="outline-status' in render_js
    assert 'class="outline-drag-handle"' not in render_js
    assert 'class="outline-actions"' not in render_js
    assert 'manualPageTemplateSelect' not in render_js
    assert "Drag page handles to reorder" not in render_js


def test_ui17_inspector_keeps_core_editing_tools_visible():
    source = _frontend_source()

    assert "Style / size" in source
    assert "inspectorTextStylePreset" in source
    assert "inspectorColorPreset" in source
    assert "inspectorCompactSpacingBtn" in source
    assert "inspectorNormalSpacingBtn" in source
    assert "inspectorAddNoteBlockBtn" in source
    assert "inspectorAddDividerBtn" in source
    assert "Select text or a rich text block" in source
    assert "if (!canStyle) return '';" not in source
