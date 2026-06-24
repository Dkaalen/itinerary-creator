from pathlib import Path


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


def test_cleanup1_keeps_review_navigation_logic_centralized():
    readiness_js = _read("visual_editor_component/frontend/js/editor_readiness.js")
    render_js = _read("visual_editor_component/frontend/js/render.js")

    assert readiness_js.count("function warningActionLabel") == 1
    assert readiness_js.count("warningActionLabel(pageId)") >= 2
    assert "function warningActionLabel" not in render_js
    assert "Go to page</button>" not in readiness_js
    assert "Review page</button>" not in readiness_js


def test_cleanup1_selection_reveal_does_not_mutate_document_model():
    selection_js = _read("visual_editor_component/frontend/js/editor_inspector_selection.js")
    body = selection_js.split("function revealSelectedInspectorTarget", 1)[1]

    assert "collect();" not in body
    assert "markTouched(" not in body
    assert "setByPath(" not in body
    assert "draw();" not in body
