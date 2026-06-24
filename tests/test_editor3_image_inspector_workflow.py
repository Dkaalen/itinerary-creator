from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


def test_canvas_image_controls_are_restored_to_hover_toolbar():
    images_js = _read("visual_editor_component/frontend/js/images.js")
    image_tools_js = _read("visual_editor_component/frontend/js/editor_image_tools.js")
    image_handlers_js = _read("visual_editor_component/frontend/js/editor_image_event_handlers.js")
    page_handlers_js = _read("visual_editor_component/frontend/js/editor_page_event_handlers.js")
    css = read_resolved_frontend_css()

    assert 'data-select-image-field="days.${dayIndex}.image"' in images_js
    assert 'data-select-image-field="${escAttr(fieldKey)}"' in image_tools_js
    assert "selectEditorFieldByKey" in page_handlers_js
    assert "data-img-bank" in images_js
    assert "data-cover-img-bank" in image_tools_js
    assert "data-img-action" in images_js
    assert "data-cover-img-action" in image_tools_js
    assert "data-img-upload" in images_js
    render_js = _read("visual_editor_component/frontend/js/render.js")
    assert "hover an image to edit it on the canvas" in render_js
    assert "pointer-events: none" in css
    assert ".image-stage:hover .image-actions" in css


def test_image_crop_focus_updates_without_full_redraw():
    image_handlers_js = _read("visual_editor_component/frontend/js/editor_image_event_handlers.js")
    state_js = _read("visual_editor_component/frontend/js/state.js")

    assert "function imageFocusLabel" in state_js
    assert "data-img-focus" in image_handlers_js
    assert "data-cover-img-focus" in image_handlers_js
    assert "style.objectPosition = focusPos(sel.value)" in image_handlers_js
    focus_section = image_handlers_js[image_handlers_js.index("document.querySelectorAll('[data-img-focus]')"):]
    assert "draw();" not in focus_section

def test_right_inspector_has_compact_selection_context():
    selection_js = _read("visual_editor_component/frontend/js/editor_inspector_selection.js")
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    css = read_resolved_frontend_css()

    assert "renderInspectorSelectionCard" in selection_js
    assert "Selection" in selection_js
    assert "renderInspectorSelectionCard" in inspector_js
    assert "selection-card" in css
    assert "canvas-image-tools" in css
