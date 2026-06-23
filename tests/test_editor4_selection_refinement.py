from pathlib import Path


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


def test_editor4_selection_card_exposes_reveal_and_clear_actions():
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    css = _read("visual_editor_component/frontend/styles/editor.css")

    assert "Reveal on page" in inspector_js
    assert "Clear selection" in inspector_js
    assert "inspectorRevealSelectionBtn" in inspector_js
    assert "inspectorClearSelectionBtn" in inspector_js
    assert "selection-actions" in css


def test_editor4_reveal_selection_scrolls_without_redrawing():
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    function_body = inspector_js.split("function revealSelectedInspectorTarget", 1)[1].split("function renderInspectorTextTools", 1)[0]

    assert "scrollIntoView({behavior: 'smooth', block: 'center'})" in function_body
    assert "selection-reveal-pulse" in function_body
    assert "updateSelectionUi();" in function_body
    assert "draw();" not in function_body
