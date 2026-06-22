function markTouched(key) {
  if (key) touchedKeys.add(key);
  persistLocalDraft();
  updateSaveState('dirty', {message: 'Unsaved edits', error: ''});
  scheduleServerAutosave();
  updateEditorStats();
}
function dirtyKeysForPage(pageId) {
  const id = String(pageId || '');
  if (!id) return [];
  return Array.from(touchedKeys || []).filter(key => {
    if (key === 'document_pages') return true;
    const meta = inferEditorBlockMetaForKey(key, '');
    return String(meta?.page_id || '') === id;
  });
}
function dirtyKeysForBlock(blockId) {
  const id = String(blockId || '');
  if (!id) return [];
  return Array.from(touchedKeys || []).filter(key => {
    const meta = inferEditorBlockMetaForKey(key, '');
    return String(meta?.block_id || '') === id;
  });
}
function pageHasDirtyEdits(pageId) {
  return dirtyKeysForPage(pageId).length > 0;
}
function blockHasDirtyEdits(blockId) {
  return dirtyKeysForBlock(blockId).length > 0;
}
function saveRecoveryPanelHtml() {
  return `<div id="saveRecoveryCard" class="save-recovery-card ${escAttr(saveState.state)}">
    <div><strong id="saveStatusLabel">${esc(saveStatusLabel())}</strong><span id="saveStatusDetail">${esc(saveStatusDetail())}</span></div>
    <em id="saveServerStatus">${esc(saveState.serverSavedAt ? `Server autosaved ${humanTime(saveState.serverSavedAt)}` : 'Server autosave ready')}</em>
  </div>`;
}
