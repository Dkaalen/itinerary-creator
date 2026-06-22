from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/render.js",
            "js/editor_inspector.js",
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


def test_ui15_prevents_preview_from_sliding_under_sidebars():
    source = _frontend_source()

    assert "max-width: 1460px" in source
    assert "grid-template-columns: minmax(198px, 228px) minmax(0, 1fr) minmax(232px, 282px)" in source
    assert ".page-stack" in source
    assert "min-width: 0" in source
    assert "overflow-x: auto" in source
    assert ".page-stack .page-wrap" in source


def test_ui15_keeps_sidebars_sticky_and_screen_fitted():
    source = _frontend_source()

    assert ".document-outline," in source
    assert ".right-inspector" in source
    assert "position: sticky" in source
    assert "top: 94px" in source
    assert "max-height: calc(100vh - 108px)" in source
    assert "overscroll-behavior: contain" in source


def test_ui15_removes_redundant_outline_page_move_buttons():
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")

    assert "const orderingActions = '';" in render_js
    assert 'title="Move page up"' not in render_js
    assert 'title="Move page down"' not in render_js
    assert "Drag page handles to reorder" in render_js
    assert "data-doc-page-action=\"hide\"" in render_js
    assert "data-doc-page-action=\"duplicate\"" in render_js


def test_ui15_inspector_hides_irrelevant_default_sections():
    source = _frontend_source()

    assert "if (!canStyle) return '';" in source
    assert "inspector-empty-state" in source
    assert "field-list-card" in source
    assert "source-card" in source
    assert "validation-card" in source
    assert "actions-card" in source
    assert "Click the canvas or page outline to show only the tools relevant" in source
