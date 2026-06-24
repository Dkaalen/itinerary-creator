from pathlib import Path

FRONTEND_JS = Path("visual_editor_component/frontend/js")

SIDEBAR_IMAGE_BLOAT = (
    "IMAGE TOOLS",
    "Image tools",
    "WHY THIS IMAGE",
    "Why this image",
    "CROP POSITION",
    "Crop position",
    "REPLACEMENT IMAGE",
    "Replacement image",
    "Use selected",
    "Remove image",
    "Upload",
    "renderInspectorImageTools",
    "inspectorImageFocus",
    "inspectorImageBank",
    "inspectorImageUploadInput",
)

NORMAL_SHELL_BLOAT = (
    "Document checks",
    "Export checks",
    "Autosave ready",
    "Server autosave ready",
    "Advanced tools",
    "review-center",
    "warningCount",
    "pdfReadinessBadgeHtml",
    "pdfReadinessBadge",
)


def test_right_inspector_files_do_not_render_sidebar_image_tools():
    inspector_sources = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_JS.glob("editor_inspector*.js"))

    for phrase in SIDEBAR_IMAGE_BLOAT:
        assert phrase not in inspector_sources


def test_canvas_image_tools_remain_available_outside_sidebar():
    canvas_sources = "\n".join(
        (FRONTEND_JS / name).read_text(encoding="utf-8")
        for name in ("images.js", "editor_image_tools.js", "editor_image_event_handlers.js")
    )

    assert "Replacement image" in canvas_sources
    assert "Use selected" in canvas_sources
    assert "Upload" in canvas_sources
    assert "data-img-action" in canvas_sources
    assert "data-cover-img-action" in canvas_sources


def test_normal_editor_shell_does_not_render_debug_review_status_bloat():
    normal_sources = "\n".join(
        (FRONTEND_JS / name).read_text(encoding="utf-8")
        for name in ("render.js", "state.js", "editor_dirty_state.js")
    )

    for phrase in NORMAL_SHELL_BLOAT:
        assert phrase not in normal_sources


def test_debug_review_bloat_is_behind_explicit_debug_boundary():
    debug_source = (FRONTEND_JS / "editor_debug_shell.js").read_text(encoding="utf-8")
    readiness_source = (FRONTEND_JS / "editor_readiness.js").read_text(encoding="utf-8")

    assert "function editorDebugModeEnabled" in debug_source
    assert "return reviewCenterHtml();" in debug_source
    assert "Advanced tools" in debug_source
    assert "Document checks" in readiness_source
    assert "Export checks" in readiness_source
