from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_ui15_keeps_review_center_behind_debug_boundary():
    source = _frontend_source()
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    debug_js = Path("visual_editor_component/frontend/js/editor_debug_shell.js").read_text(encoding="utf-8")

    assert "reviewCenterHtml" in source
    assert 'class="review-center"' in source
    assert "Document checks" in source
    assert "review-center-grid" in source
    assert 'class="warning-panel warning-group ${escAttr(className)}"' in source
    assert 'class="pdf-readiness-panel ${escAttr(status.level)}"><summary>' in source
    assert "editorDebugReviewHtml" in render_js
    assert "${reviewCenterHtml()}" not in render_js
    assert "return reviewCenterHtml();" in debug_js


def test_ui18_protects_canvas_with_internal_workspace_scroll():
    source = _frontend_source()

    assert "grid-template-columns: minmax(var(--page-w), var(--page-w)) minmax(270px, 292px)" in source
    assert 'grid-template-areas: "canvas inspector"' in source
    assert "height: auto" in source
    assert ".page-stack .page-wrap" in source
    assert "width: var(--page-w)" in source
    assert "overflow: visible" in source
    assert "overflow-x: hidden" in source


def test_ui18_keeps_formatting_sidebar_visible_while_canvas_scrolls():
    source = _frontend_source()

    assert ".right-inspector" in source
    assert "position: sticky !important" in source
    assert "height: auto" in source
    assert "max-height: calc(100vh - 112px)" in source
    assert "overflow-y: auto" in source
    assert "grid-area: inspector" in source


def test_ui18_page_navigation_is_collapsed_not_a_permanent_left_sidebar():
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    outline_js = Path("visual_editor_component/frontend/js/editor_document_outline.js").read_text(encoding="utf-8")
    css = read_resolved_frontend_css()

    assert 'class="pages-menu"' in outline_js
    assert '${renderDocumentOutline()}' in outline_js
    assert '${renderDocumentOutline()}\n      <div class="page-stack">' not in render_js
    assert '.editor-workspace > .document-outline {' in css
    assert 'display: none !important;' in css
    assert 'class="outline-drag-handle"' not in render_js
    assert 'class="outline-actions"' not in render_js

def test_ui18_inspector_keeps_word_style_formatting_tools_visible():
    source = _frontend_source()

    assert "Font" in source
    assert "Size" in source
    assert "Text color / highlight" in source
    assert "inspectorFontFamilyPreset" in source
    assert "inspectorFontSizePreset" in source
    assert "inspectorTextStylePreset" in source
    assert "inspectorColorPreset" in source
    assert "inspectorCompactSpacingBtn" in source
    assert "inspectorNormalSpacingBtn" in source
    assert "Formatting applies to the selected canvas text" in source
    assert "if (!canStyle) return '';" not in source


def test_ui20_uses_internal_canvas_scroll_instead_of_expanding_iframe():
    css = read_resolved_frontend_css()
    ui20 = css[css.index("UI20 editor foundation fix"):]

    assert "body {" in ui20
    assert "overflow: hidden" in ui20
    assert ".page-stack" in ui20
    assert "overflow-y: auto !important" in ui20
    assert "height: 100% !important" in ui20
    assert ".right-inspector" in ui20
    assert "max-height: 100% !important" in ui20


def test_ui20_selection_styles_do_not_change_layout_dimensions():
    css = read_resolved_frontend_css()
    ui20 = css[css.index("UI20 editor foundation fix"):]

    assert ".selected-editor-block" in ui20
    assert "outline: 2px solid" in ui20
    assert "border: 0 !important" in ui20
    assert ".page-wrap.selected-page > .page-header-row" in ui20
    assert "padding: 0 !important" in ui20
