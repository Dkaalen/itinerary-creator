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


def test_right_inspector_exposes_layout_tools():
    source = _frontend_source()

    assert "renderInspectorLayoutTools" in source
    assert "inspectorPageSpacing" in source
    assert "inspectorKeepPageTogether" in source
    assert "inspectorBlockSpacing" in source
    assert "inspectorKeepBlockTogether" in source
    assert "inspectorHidePageBtn" in source
    assert "inspectorRestorePageBtn" in source
    assert "inspectorResetPageLayoutBtn" in source
    assert "layout-tools-card" in source


def test_manual_page_block_layout_actions_are_available():
    source = _frontend_source()

    assert "addManualTextBlockToSelectedPage" in source
    assert "duplicateSelectedManualBlock" in source
    assert "moveSelectedManualBlock" in source
    assert "deleteSelectedManualBlock" in source
    assert "inspectorAddManualBlockBtn" in source
    assert "inspectorMoveBlockUpBtn" in source
    assert "inspectorMoveBlockDownBtn" in source
    assert "inspectorDuplicateBlockBtn" in source
    assert "inspectorDeleteBlockBtn" in source
    assert "manual-block-shell" in source


def test_layout_overrides_are_stored_in_document_pages_contract():
    source = _frontend_source()

    assert "ensurePageOverrides" in source
    assert "ensureBlockStyleOverrides" in source
    assert "page.page_overrides" in source
    assert "block.style_overrides" in source
    assert "markDocumentPagesTouched('Page layout updated')" in source
    assert "markDocumentPagesTouched('Block layout updated')" in source
    assert "layout-density-compact" in source
    assert "layout-density-comfortable" in source
