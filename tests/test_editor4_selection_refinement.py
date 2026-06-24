from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


def test_editor4_selection_card_exposes_reveal_and_clear_actions():
    selection_js = _read("visual_editor_component/frontend/js/editor_inspector_selection.js")
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    css = read_resolved_frontend_css()

    assert "Reveal on page" in selection_js
    assert "Clear selection" in selection_js
    assert "inspectorRevealSelectionBtn" in inspector_js
    assert "inspectorClearSelectionBtn" in inspector_js
    assert "selection-actions" in css


def test_editor4_reveal_selection_scrolls_without_redrawing():
    selection_js = _read("visual_editor_component/frontend/js/editor_inspector_selection.js")
    function_body = selection_js.split("function revealSelectedInspectorTarget", 1)[1]

    assert "scrollIntoView({behavior: 'smooth', block: 'center'})" in function_body
    assert "selection-reveal-pulse" in function_body
    assert "updateSelectionUi();" in function_body
    assert "draw();" not in function_body
