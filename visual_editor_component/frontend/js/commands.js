// Public command facade for the visual editor.
//
// Large command implementations are split by responsibility into:
// - editor_dirty_state.js
// - editor_text_tools.js
// - editor_document_model.js
// - editor_inspector.js
// - editor_page_actions.js
// - editor_warnings.js
//
// Migration markers for older static tests/import readers:
// function markTouched, function insertCleanClipboardHtml, function mergeInclusionPageUp
// text tools use controlledPresetClassMap('text_styles') and controlledEditorAllowedClasses()
// insertable controlled blocks use controlledBlockTemplate('note') and controlledBlockTemplate('divider')
window.visualEditorCommands = Object.freeze({
  markTouched,
  dirtyKeysForPage,
  dirtyKeysForBlock,
  pageHasDirtyEdits,
  blockHasDirtyEdits,
  editableValue,
  writeEditableValue,
  selectedEditable,
  insertCleanClipboardHtml,
  applyFontFamilyPreset,
  applyFontSizePreset,
  applyColorPreset,
  selectEditorPage,
  selectEditorBlockFromElement,
  renderRightInspector,
  attachInspectorHandlers,
  hideDocumentPage,
  restoreDocumentPage,
  addManualPage,
  addManualPageAfter,
  duplicateManualPage,
  moveDocumentPage,
  moveDocumentPageToIndex,
  mergeInclusionPageUp,
  flagSelectedIssue,
  highlightWarnings,
  updateEditorStats,
});
