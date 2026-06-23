from pathlib import Path


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


def test_cleanup1_keeps_review_navigation_logic_centralized():
    render_js = _read("visual_editor_component/frontend/js/render.js")

    assert render_js.count("function warningActionLabel") == 1
    assert render_js.count("warningActionLabel(pageId)") >= 2
    assert "Go to page</button>" not in render_js
    assert "Review page</button>" not in render_js


def test_cleanup1_selection_reveal_does_not_mutate_document_model():
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    body = inspector_js.split("function revealSelectedInspectorTarget", 1)[1].split("function renderInspectorTextTools", 1)[0]

    assert "collect();" not in body
    assert "markTouched(" not in body
    assert "setByPath(" not in body
    assert "draw();" not in body
