from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css

FRONTEND = Path("visual_editor_component/frontend")


class _AssetShellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []
        self.inline_style_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "link" and attr.get("rel") == "stylesheet" and attr.get("href"):
            self.stylesheets.append(attr["href"] or "")
        if tag == "script" and attr.get("src"):
            self.scripts.append(attr["src"] or "")
        if tag == "style":
            self.inline_style_count += 1


def _asset_shell() -> _AssetShellParser:
    parser = _AssetShellParser()
    parser.feed((FRONTEND / "index.html").read_text(encoding="utf-8"))
    return parser


def _asset_text(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8")


def _asset_contains(relative: str, token: str) -> bool:
    return token in _asset_text(relative)


def _asset_omits(relative: str, token: str) -> bool:
    return token not in _asset_text(relative)


def _all_assets_contain(expected: dict[str, list[str]]) -> list[str]:
    missing: list[str] = []
    for relative, markers in expected.items():
        for marker in markers:
            if not _asset_contains(relative, marker):
                missing.append(f"{relative}: {marker!r}")
    return missing


def test_visual_editor_index_is_thin_asset_shell():
    shell = _asset_shell()
    index_lines = (FRONTEND / "index.html").read_text(encoding="utf-8").splitlines()
    required_scripts = {
        "js/state.js",
        "js/editor_assets.js",
        "js/images.js",
        "js/editor_image_tools.js",
        "js/editor_readiness.js",
        "js/editor_debug_shell.js",
        "js/render.js",
        "js/serialization.js",
        "js/editor_dirty_state.js",
        "js/editor_text_tools.js",
        "js/editor_document_model.js",
        "js/editor_inspector_selection.js",
        "js/editor_inspector_fields.js",
        "js/editor_inspector_text_panel.js",
        "js/editor_inspector_layout_panel.js",
        "js/editor_inspector.js",
        "js/editor_page_actions.js",
        "js/editor_warnings.js",
        "js/commands.js",
        "js/editor_page_event_handlers.js",
        "js/editor_image_event_handlers.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    }

    assert shell.stylesheets == ["styles/editor.css"]
    assert set(shell.scripts) == required_scripts
    assert shell.scripts.index("js/state.js") < shell.scripts.index("js/render.js")
    assert shell.scripts.index("js/commands.js") < shell.scripts.index("js/editing.js")
    assert shell.scripts.index("js/editing.js") < shell.scripts.index("js/streamlit_bridge.js")
    assert shell.inline_style_count == 0
    assert not _asset_contains("index.html", "function render(")
    assert len(index_lines) <= 36


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

    assert _all_assets_contain(expected) == []


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
    current_styles = {path.name for path in styles_dir.glob("*.css")}
    imported_styles = set(_asset_text("styles/editor.css").replace("'", '"').split('"'))

    assert retired.isdisjoint(current_styles)
    assert retired.isdisjoint(imported_styles)


def test_visual_editor_toolbar_uses_simple_default_actions():
    css = read_resolved_frontend_css()

    assert _asset_contains("js/render.js", "Edit itinerary text")
    assert _asset_contains("js/render.js", "Review itinerary with pictures")
    assert _asset_contains("js/render.js", "Save changes")
    assert _asset_omits("js/render.js", "Advanced tools")
    assert _asset_contains("js/editor_debug_shell.js", "Advanced tools")
    assert _asset_omits("js/render.js", "Save for now")
    assert _asset_omits("js/render.js", "More edit tools")
    assert "grid-template-columns: minmax(260px, 1fr) auto;" in css
    assert "max-width: 1060px;" in css
    assert ".advanced-tools .toolbar-tools" in css


def test_image_replacement_uses_bounded_option_preview_payloads():
    assert _asset_contains("../editor_payload_images.py", "metadata_first_image_options")
    assert _asset_contains("../editor_payload_images.py", "get_image_preview_for_path(path, option=True)")
    assert _asset_omits("js/editor_inspector.js", "selected.preview_data_uri || selected.data_uri")
    assert _asset_contains("js/editor_image_event_handlers.js", "selected.preview_data_uri || selected.data_uri")
    assert _asset_omits("js/images.js", "Replacement selected — save to update preview")
    assert _asset_omits("js/editor_inspector.js", "Save changes to refresh the preview image")
    assert _asset_contains("js/images.js", "Replacement selected — preview unavailable")


def test_server_autosave_waits_for_editor_idle_when_explicitly_scheduled():
    dirty_state_before_explicit_autosave = _asset_text("js/editor_dirty_state.js").split(
        "if (options.serverAutosave === true)", 1
    )[0]

    assert _asset_contains("js/state.js", "AUTOSAVE_IDLE_GRACE_MS")
    assert _asset_contains("js/editor_save_state.js", "function noteEditorInteraction")
    assert _asset_contains("js/editor_save_state.js", "function editorIsActivelyInUse")
    assert _asset_contains("js/editing.js", "editorIsActivelyInUse(now)")
    assert _asset_contains("js/editing.js", "scheduleServerAutosave(AUTOSAVE_IDLE_GRACE_MS)")
    assert _asset_contains("js/editing.js", "addEventListener('scroll', noteEditorInteraction")
    assert _asset_contains("js/editor_dirty_state.js", "if (options.serverAutosave === true) scheduleServerAutosave()")
    assert "scheduleServerAutosave()" not in dirty_state_before_explicit_autosave


def test_image_edits_refresh_only_the_affected_image_surface():
    image_handlers = _asset_text("js/editor_image_event_handlers.js")
    day_action_block = image_handlers.split("root.querySelectorAll('[data-img-action]')", 1)[1].split(
        "root.querySelectorAll('[data-img-focus]')", 1
    )[0]
    cover_action_block = image_handlers.split("root.querySelectorAll('[data-cover-img-action]')", 1)[1].split(
        "root.querySelectorAll('[data-cover-img-focus]')", 1
    )[0]

    assert _asset_contains("js/editor_image_event_handlers.js", "function replaceDayImageStage")
    assert _asset_contains("js/editor_image_event_handlers.js", "function replaceCoverImagePanel")
    assert _asset_contains("js/editor_image_event_handlers.js", "refreshImageEditSurface('day', idx)")
    assert _asset_contains("js/editor_image_event_handlers.js", "refreshImageEditSurface('cover', key)")
    assert _asset_contains("js/editor_image_event_handlers.js", "markTouched(key, {serverAutosave: false})")
    assert _asset_omits("js/editor_image_event_handlers.js", "scheduleServerAutosave(autosaveDelayMs, true)")
    assert "collect();" not in day_action_block
    assert "collect();" not in cover_action_block
    assert "draw();" not in day_action_block
    assert "draw();" not in cover_action_block


def test_local_draft_strips_uploaded_image_binary_from_browser_storage():
    assert _asset_contains("js/editor_local_draft.js", "stripUploadBinaryForLocalDraft")
    assert _asset_contains("js/editor_local_draft.js", "delete upload.data_uri")
    assert _asset_contains("js/editor_local_draft.js", "data_omitted")


def test_replacement_options_are_bounded_and_use_tiny_previews_by_default():
    assert _asset_contains("../editor_payload_images.py", "DAY_REPLACEMENT_OPTION_LIMIT = 8")
    assert _asset_contains("../editor_payload_images.py", "OPTION_PREVIEW_LIMIT = DAY_REPLACEMENT_OPTION_LIMIT")
    assert _asset_contains("../editor_payload_images.py", "get_image_preview_for_path(path, option=True)")


def test_visual_editor_bridge_waits_for_render_and_disposes_stale_frames() -> None:
    bridge = _asset_text("js/streamlit_bridge.js")
    editing = _asset_text("js/editing.js")

    assert "streamlitBridgeRenderReceived = false" in bridge
    assert "requiresRender && !streamlitBridgeRenderReceived" in bridge
    assert "markStreamlitRenderReceived();" in bridge
    assert "pagehide" in bridge
    assert "beforeunload" in bridge
    assert "if (!Streamlit.setComponentValue(serialized))" in editing
