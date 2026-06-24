// Debug-only editor shell panels. Normal users get the clean PDF-producing workflow.
function editorDebugModeEnabled() {
  if (model?.workflow?.editor_debug || initialPayload?.workflow?.editor_debug) return true;
  try {
    return window.localStorage?.getItem('itineraryEditorDebug') === '1';
  } catch (err) {
    return false;
  }
}

function editorDebugToolbarHtml() {
  if (!editorDebugModeEnabled()) return '';
  return `<div class="debug-editor-shell">
    ${saveRecoveryPanelHtml()}
    <details class="advanced-tools">
      <summary>Advanced tools</summary>
      ${studioStatusStripHtml()}
      <div class="toolbar-tools">
        <button class="ghost" id="undoBtn" type="button">Undo</button>
        <button class="ghost" id="resetBlockBtn" type="button">Reset section</button>
        <button class="ghost" id="resetBtn" type="button">Reset draft</button>
        <input id="findText" type="text" placeholder="Find text">
        <input id="replaceText" type="text" placeholder="Replace with">
        <button class="ghost" id="replaceBtn" type="button">Replace all</button>
        <button class="ghost" id="flagIssueBtn" type="button">Flag issue</button>
        <span id="savedNote" class="saved-note">Ready</span>
      </div>
    </details>
  </div>`;
}

function editorDebugReviewHtml() {
  if (!editorDebugModeEnabled()) return '';
  return reviewCenterHtml();
}
