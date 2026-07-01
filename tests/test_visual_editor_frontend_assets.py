from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css

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
    assert '<script src="js/editor_debug_shell.js"></script>' in index
    assert '<script src="js/render.js"></script>' in index
    assert '<script src="js/serialization.js"></script>' in index
    assert '<script src="js/editor_dirty_state.js"></script>' in index
    assert '<script src="js/editor_text_tools.js"></script>' in index
    assert '<script src="js/editor_document_model.js"></script>' in index
    assert '<script src="js/editor_inspector_selection.js"></script>' in index
    assert '<script src="js/editor_inspector_fields.js"></script>' in index
    assert '<script src="js/editor_inspector_text_panel.js"></script>' in index
    assert '<script src="js/editor_inspector_layout_panel.js"></script>' in index
    assert '<script src="js/editor_inspector.js"></script>' in index
    assert '<script src="js/editor_page_actions.js"></script>' in index
    assert '<script src="js/editor_warnings.js"></script>' in index
    assert '<script src="js/commands.js"></script>' in index
    assert '<script src="js/editing.js"></script>' in index
    assert '<script src="js/streamlit_bridge.js"></script>' in index
    assert "<style>" not in index
    assert "function render(" not in index
    assert len(index.splitlines()) <= 36


def test_visual_editor_frontend_assets_are_split_by_responsibility():
    expected = {
        "styles/editor.css": ['@import url("editor_tokens.css")', '@import url("editor_responsive.css")'],
        "styles/editor_tokens.css": ["Visual editor design tokens", ":root"],
        "styles/editor_base.css": ["Visual editor base document", "button.primary"],
        "styles/editor_pages.css": ["Visual editor page and itinerary content", ".a4-page"],
        "styles/editor_shell.css": ["Visual editor outer shell styles", ".editor-shell"],
        "styles/editor_canvas_workspace.css": ["Visual editor workspace", ".editor-workspace"],
        "styles/editor_outline.css": ["Visual editor document outline", ".document-outline"],
        "styles/editor_page_actions.css": ["Visual editor page action", ".page-action-menu"],
        "styles/editor_toolbar.css": ["Visual editor toolbar", ".editor-toolbar"],
        "styles/editor_text_tools.css": ["Visual editor text tool", ".ve-font-dm-sans"],
        "styles/editor_image_tools.css": ["Visual editor canvas image toolbars", ".image-stage:hover .image-actions"],
        "styles/editor_inspector.css": ["Visual editor inspector shell", ".selection-actions"],
        "styles/editor_layout_tools.css": ["Visual editor layout-density"],
        "styles/editor_manual_pages.css": ["Visual editor manual page", ".manual-page"],
        "styles/editor_final_pages.css": ["Visual editor final page"],
        "styles/editor_debug.css": ["Visual editor debug-only readiness", ".review-center"],
        "styles/editor_responsive.css": ["Visual editor responsive", "@media"],
        "js/state.js": ["let initialPayload", "AUTOSAVE_IDLE_GRACE_MS"],
        "js/editor_local_draft.js": ["function restoreLocalDraftIfAvailable", "function persistLocalDraft"],
        "js/images.js": ["function imageHtml", "function adjustDayImages"],
        "js/editor_image_tools.js": ["function coverImageControls", "canvas-image-tools"],
        "js/editor_warning_model.js": ["function pdfReadinessStatus", "function warningTargetPageId"],
        "js/editor_debug_readiness.js": ["function pdfReadinessPanelHtml", "function reviewCenterHtml"],
        "js/editor_debug_shell.js": ["function editorDebugModeEnabled", "function editorDebugToolbarHtml"],
        "js/render.js": ["function render(", "function draw()"],
        "js/serialization.js": ["function collect()", "function buildEditableDraftFromPayload", "function buildSaveEnvelope"],
        "js/editor_dirty_state.js": ["function markTouched", "function saveRecoveryPanelHtml"],
        "js/editor_insert_blocks.js": ["function insertControlledBlock", "function addNoteBlock"],
        "js/editor_paste_sanitizer.js": ["function insertCleanClipboardHtml"],
        "js/editor_text_formatting.js": ["function applyTextStylePreset", "function applyFontFamilyPreset"],
        "js/editor_pages_model.js": ["function documentPages", "function sortedDocumentPages"],
        "js/editor_manual_pages.js": ["function manualPageFromTemplate", "function addManualBlockToSelectedPage"],
        "js/editor_document_model.js": ["function editorSlug", "function htmlTextContent"],
        "js/editor_inspector_selection.js": ["function selectedInspectorMeta", "function renderInspectorSelectionCard"],
        "js/editor_inspector_fields.js": ["function inspectorFieldEntriesForSelection", "function applyInspectorFieldEdit"],
        "js/editor_inspector_text_panel.js": ["function renderInspectorTextTools", "inspectorFontFamilyPreset"],
        "js/editor_inspector_layout_panel.js": ["function renderInspectorLayoutTools", "inspectorPageSpacing"],
        "js/editor_inspector.js": ["function renderRightInspector", "function attachInspectorHandlers"],
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


def test_visual_editor_css_does_not_use_patch_history_files():
    styles_dir = FRONTEND / "styles"
    retired = {
        "editor_foundation.css",
        "editor_core.css",
        "editor_workspace.css",
        "editor_workspace_corrections.css",
        "editor_workspace_late.css",
        "editor_workspace_final.css",
        "editor_review.css",
        "editor_review_final.css",
        "editor_image_inspector.css",
        "editor_text_presets.css",
        "editor_text_presets_final.css",
    }

    assert retired.isdisjoint({path.name for path in styles_dir.glob("*.css")})
    imports = (styles_dir / "editor.css").read_text(encoding="utf-8")
    for name in retired:
        assert name not in imports


def test_visual_editor_toolbar_uses_simple_default_actions():
    render_js = (FRONTEND / "js/render.js").read_text(encoding="utf-8")
    css = read_resolved_frontend_css()

    assert "Edit itinerary text" in render_js
    assert "Review itinerary with pictures" in render_js
    assert "Save changes" in render_js
    assert "Advanced tools" not in render_js
    assert "Advanced tools" in (FRONTEND / "js/editor_debug_shell.js").read_text(encoding="utf-8")
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
    assert "selected.preview_data_uri || selected.data_uri" not in inspector
    assert "selected.preview_data_uri || selected.data_uri" in image_handlers
    assert "Replacement selected — save to update preview" not in images
    assert "Save changes to refresh the preview image" not in inspector


def test_server_autosave_waits_for_editor_idle_when_explicitly_scheduled():
    state = (FRONTEND / "js/state.js").read_text(encoding="utf-8")
    save_state = (FRONTEND / "js/editor_save_state.js").read_text(encoding="utf-8")
    editing = (FRONTEND / "js/editing.js").read_text(encoding="utf-8")

    assert "AUTOSAVE_IDLE_GRACE_MS" in state
    assert "function noteEditorInteraction" in save_state
    assert "function editorIsActivelyInUse" in save_state
    dirty_state = (FRONTEND / "js/editor_dirty_state.js").read_text(encoding="utf-8")

    assert "editorIsActivelyInUse(now)" in editing
    assert "scheduleServerAutosave(AUTOSAVE_IDLE_GRACE_MS)" in editing
    assert "addEventListener('scroll', noteEditorInteraction" in editing
    assert "if (options.serverAutosave === true) scheduleServerAutosave()" in dirty_state
    assert "scheduleServerAutosave()" not in dirty_state.split("if (options.serverAutosave === true)", 1)[0]


def test_image_edits_refresh_only_the_affected_image_surface():
    image_handlers = (FRONTEND / "js/editor_image_event_handlers.js").read_text(encoding="utf-8")

    assert "function replaceDayImageStage" in image_handlers
    assert "function replaceCoverImagePanel" in image_handlers
    assert "refreshImageEditSurface('day', idx)" in image_handlers
    assert "refreshImageEditSurface('cover', key)" in image_handlers
    assert "markTouched(key, {serverAutosave: false})" in image_handlers
    assert "scheduleServerAutosave(autosaveDelayMs, true)" not in image_handlers

    day_action_block = image_handlers.split("root.querySelectorAll('[data-img-action]')", 1)[1].split("root.querySelectorAll('[data-img-focus]')", 1)[0]
    cover_action_block = image_handlers.split("root.querySelectorAll('[data-cover-img-action]')", 1)[1].split("root.querySelectorAll('[data-cover-img-focus]')", 1)[0]
    assert "collect();" not in day_action_block
    assert "collect();" not in cover_action_block
    assert "draw();" not in day_action_block
    assert "draw();" not in cover_action_block


def test_local_draft_strips_uploaded_image_binary_from_browser_storage():
    local_draft = (FRONTEND / "js/editor_local_draft.js").read_text(encoding="utf-8")

    assert "stripUploadBinaryForLocalDraft" in local_draft
    assert "delete upload.data_uri" in local_draft
    assert "data_omitted" in local_draft


def test_replacement_options_all_receive_small_previews():
    payload = Path("visual_editor_component/editor_payload_images.py").read_text(encoding="utf-8")

    assert "DAY_REPLACEMENT_OPTION_LIMIT = 8" in payload
    assert "OPTION_PREVIEW_LIMIT = DAY_REPLACEMENT_OPTION_LIMIT" in payload
