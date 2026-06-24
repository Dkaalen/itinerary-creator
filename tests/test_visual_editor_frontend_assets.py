from pathlib import Path

FRONTEND = Path("visual_editor_component/frontend")


def test_visual_editor_index_is_thin_asset_shell():
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="styles/editor.css" />' in index
    assert '<script src="js/editor_page_event_handlers.js"></script>' in index
    assert '<script src="js/editor_image_event_handlers.js"></script>' in index
    assert '<script src="js/state.js"></script>' in index
    assert '<script src="js/images.js"></script>' in index
    assert '<script src="js/editor_image_tools.js"></script>' in index
    assert '<script src="js/editor_readiness.js"></script>' in index
    assert '<script src="js/render.js"></script>' in index
    assert '<script src="js/serialization.js"></script>' in index
    assert '<script src="js/editor_dirty_state.js"></script>' in index
    assert '<script src="js/editor_text_tools.js"></script>' in index
    assert '<script src="js/editor_document_model.js"></script>' in index
    assert '<script src="js/editor_inspector.js"></script>' in index
    assert '<script src="js/editor_page_actions.js"></script>' in index
    assert '<script src="js/editor_warnings.js"></script>' in index
    assert '<script src="js/commands.js"></script>' in index
    assert '<script src="js/editing.js"></script>' in index
    assert '<script src="js/streamlit_bridge.js"></script>' in index
    assert "<style>" not in index
    assert "function render(" not in index
    assert len(index.splitlines()) <= 30


def test_visual_editor_frontend_assets_are_split_by_responsibility():
    expected = {
        "styles/editor.css": ['@import url("editor_foundation.css")', '@import url("editor_core.css")'],
        "styles/editor_core.css": [".editor-toolbar", ".advanced-tools", ".a4-page"],
        "styles/editor_foundation.css": ["Visual editor foundation styles"],
        "styles/editor_workspace.css": ["Visual editor workspace/page-shell styles"],
        "styles/editor_review.css": ["Visual editor review/readiness styles"],
        "js/state.js": ["let initialPayload", "function restoreLocalDraftIfAvailable"],
        "js/images.js": ["function imageHtml", "function adjustDayImages"],
        "js/editor_image_tools.js": ["function coverImageControls", "canvas-image-tools"],
        "js/editor_readiness.js": ["function pdfReadinessStatus", "function reviewCenterHtml"],
        "js/render.js": ["function render(", "function draw()"],
        "js/serialization.js": ["function collect()", "function buildEditableDraftFromPayload", "function buildSaveEnvelope"],
        "js/editor_dirty_state.js": ["function markTouched", "function saveRecoveryPanelHtml"],
        "js/editor_text_tools.js": ["function insertCleanClipboardHtml", "function applyTextStylePreset"],
        "js/editor_document_model.js": ["function documentPages", "function manualPageFromTemplate"],
        "js/editor_inspector.js": ["function renderRightInspector", "function renderInspectorTextTools"],
        "js/editor_page_actions.js": ["function mergeInclusionPageUp", "function addManualPage"],
        "js/editor_warnings.js": ["function highlightWarnings", "function updateEditorStats"],
        "js/commands.js": ["window.visualEditorCommands", "Public command facade"],
        "js/editor_page_event_handlers.js": ["function attachPageEventHandlers", "data-outline-page-id"],
        "js/editor_image_event_handlers.js": ["function attachImageEventHandlers", "data-img-action"],
        "js/editing.js": ["function saveChanges", "function attachHandlers"],
        "js/streamlit_bridge.js": ["const Streamlit", "streamlit:render"],
    }

    for relative, markers in expected.items():
        body = (FRONTEND / relative).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in body, f"{marker!r} missing from {relative}"


def test_visual_editor_toolbar_uses_simple_default_actions():
    render_js = (FRONTEND / "js/render.js").read_text(encoding="utf-8")
    css = (FRONTEND / "styles/editor_core.css").read_text(encoding="utf-8")

    assert "Edit itinerary text" in render_js
    assert "Review itinerary with pictures" in render_js
    assert "Save changes" in render_js
    assert "Advanced tools" in render_js
    assert "Save for now" not in render_js
    assert "More edit tools" not in render_js
    assert "grid-template-columns: minmax(260px, 1fr) auto;" in css
    assert "max-width: 1060px;" in css
    assert ".advanced-tools .toolbar-tools" in css


def test_image_replacement_uses_instant_option_preview_not_muted_placeholder():
    inspector = (FRONTEND / "js/editor_inspector.js").read_text(encoding="utf-8")
    image_handlers = (FRONTEND / "js/editor_image_event_handlers.js").read_text(encoding="utf-8")
    images = (FRONTEND / "js/images.js").read_text(encoding="utf-8")
    payload = Path("visual_editor_component/editor_payload_images.py").read_text(encoding="utf-8")

    assert "preview_data_uri" in payload
    assert "get_image_preview_for_path(path, option=True)" in payload
    assert "selected.preview_data_uri || selected.data_uri" in inspector
    assert "selected.preview_data_uri || selected.data_uri" in image_handlers
    assert "Replacement selected — save to update preview" not in images
    assert "Save changes to refresh the preview image" not in inspector


def test_server_autosave_waits_for_editor_idle_instead_of_interrupting_scroll():
    state = (FRONTEND / "js/state.js").read_text(encoding="utf-8")
    editing = (FRONTEND / "js/editing.js").read_text(encoding="utf-8")

    assert "AUTOSAVE_IDLE_GRACE_MS" in state
    assert "function noteEditorInteraction" in state
    assert "function editorIsActivelyInUse" in state
    assert "editorIsActivelyInUse(now)" in editing
    assert "scheduleServerAutosave(AUTOSAVE_IDLE_GRACE_MS)" in editing
    assert "addEventListener('scroll', noteEditorInteraction" in editing
