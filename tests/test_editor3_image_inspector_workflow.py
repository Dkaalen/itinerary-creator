from pathlib import Path


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


def test_canvas_image_controls_are_restored_to_hover_toolbar():
    images_js = _read("visual_editor_component/frontend/js/images.js")
    image_tools_js = _read("visual_editor_component/frontend/js/editor_image_tools.js")
    image_handlers_js = _read("visual_editor_component/frontend/js/editor_image_event_handlers.js")
    page_handlers_js = _read("visual_editor_component/frontend/js/editor_page_event_handlers.js")
    css = _read("visual_editor_component/frontend/styles/editor_core.css")

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
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    state_js = _read("visual_editor_component/frontend/js/state.js")

    assert "function imageFocusLabel" in state_js
    assert "function updateImagePreviewForContext" in inspector_js
    assert "if (action === 'focus')" in inspector_js
    assert "updateImagePreviewForContext(ctx);" in inspector_js
    assert "draw();" in inspector_js


def test_right_inspector_has_compact_selection_context():
    inspector_js = _read("visual_editor_component/frontend/js/editor_inspector.js")
    css = _read("visual_editor_component/frontend/styles/editor_core.css")

    assert "renderInspectorSelectionCard" in inspector_js
    assert "Selection" in inspector_js
    assert "selection-card" in css
    assert "canvas-image-tools" in css
