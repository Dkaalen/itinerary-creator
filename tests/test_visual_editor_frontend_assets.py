from pathlib import Path

FRONTEND = Path("visual_editor_component/frontend")


def test_visual_editor_index_is_thin_asset_shell():
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="styles/editor.css" />' in index
    assert '<script src="js/state.js"></script>' in index
    assert '<script src="js/images.js"></script>' in index
    assert '<script src="js/render.js"></script>' in index
    assert '<script src="js/editing.js"></script>' in index
    assert '<script src="js/streamlit_bridge.js"></script>' in index
    assert "<style>" not in index
    assert "function render(" not in index
    assert len(index.splitlines()) <= 30


def test_visual_editor_frontend_assets_are_split_by_responsibility():
    expected = {
        "styles/editor.css": [".editor-toolbar", ".advanced-tools", ".a4-page"],
        "js/state.js": ["let initialPayload", "function restoreLocalDraftIfAvailable"],
        "js/images.js": ["function imageHtml", "function adjustDayImages"],
        "js/render.js": ["function render(", "function draw()"],
        "js/editing.js": ["function collect()", "function saveChanges", "function attachHandlers"],
        "js/streamlit_bridge.js": ["const Streamlit", "streamlit:render"],
    }

    for relative, markers in expected.items():
        body = (FRONTEND / relative).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in body, f"{marker!r} missing from {relative}"


def test_visual_editor_toolbar_uses_simple_default_actions():
    render_js = (FRONTEND / "js/render.js").read_text(encoding="utf-8")
    css = (FRONTEND / "styles/editor.css").read_text(encoding="utf-8")

    assert "Edit itinerary text" in render_js
    assert "Review itinerary with pictures" in render_js
    assert "Save changes" in render_js
    assert "Advanced tools" in render_js
    assert "Save for now" not in render_js
    assert "More edit tools" not in render_js
    assert "grid-template-columns: minmax(260px, 1fr) auto;" in css
    assert "max-width: 1060px;" in css
    assert ".advanced-tools .toolbar-tools" in css
