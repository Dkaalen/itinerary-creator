/** Responsibility split from editor_document_model.js. */
function selectEditorPage(pageId) {
  const nextPageId = pageId;
  const changed = activePageId !== nextPageId || activeBlockId !== null || activeFieldKey !== null;
  activePageId = nextPageId;
  activeBlockId = null;
  activeFieldKey = null;
  updateSelectionUi();
  if (changed) updateRightInspector();
}

function selectEditorFieldByKey(fieldKey) {
  const key = String(fieldKey || '');
  if (!key) return;
  const target = document.querySelector(`[data-editor-field-key="${CSS.escape(key)}"]`) || document.querySelector(`[data-edit-key="${CSS.escape(key)}"]`);
  if (target) {
    selectEditorBlockFromElement(target);
    return;
  }
  const meta = inferEditorBlockMetaForKey(key, '');
  activePageId = meta.page_id || activePageId;
  activeBlockId = meta.block_id || activeBlockId;
  activeFieldKey = key;
  updateSelectionUi();
  updateRightInspector();
}

function selectEditorBlockFromElement(el) {
  const target = el?.closest?.('[data-editor-block-id]') || el?.closest?.('[data-edit-key]');
  if (!target) return;
  const meta = inferEditorBlockMetaForKey(target.getAttribute('data-editor-field-key') || target.getAttribute('data-edit-key') || '', target.getAttribute('data-editor-field-label') || '');
  const nextPageId = target.getAttribute('data-editor-page-id') || meta.page_id || target.closest('[data-page-id]')?.getAttribute('data-page-id') || activePageId;
  const nextBlockId = target.getAttribute('data-editor-block-id') || meta.block_id || '';
  const nextFieldKey = target.getAttribute('data-editor-field-key') || target.getAttribute('data-edit-key') || '';
  const changed = activePageId !== nextPageId || activeBlockId !== nextBlockId || activeFieldKey !== nextFieldKey;
  activePageId = nextPageId;
  activeBlockId = nextBlockId;
  activeFieldKey = nextFieldKey;
  updateSelectionUi();
  if (changed) updateRightInspector();
}

function selectedEditorElement() {
  if (activeFieldKey) {
    const byField = document.querySelector(`[data-editor-field-key="${CSS.escape(activeFieldKey)}"]`) || document.querySelector(`[data-edit-key="${CSS.escape(activeFieldKey)}"]`);
    if (byField) return byField;
  }
  if (activeBlockId) return document.querySelector(`[data-editor-block-id="${CSS.escape(activeBlockId)}"]`);
  return selectedEditable();
}

function updateSelectionUi() {
  document.querySelectorAll('[data-page-id]').forEach(el => el.classList.toggle('selected-page', el.getAttribute('data-page-id') === activePageId));
  document.querySelectorAll('[data-outline-page-id]').forEach(el => el.classList.toggle('active', el.getAttribute('data-outline-page-id') === activePageId));
  document.querySelectorAll('[data-editor-block-id]').forEach(el => {
    const blockMatch = activeBlockId && el.getAttribute('data-editor-block-id') === activeBlockId;
    const fieldMatch = activeFieldKey && (el.getAttribute('data-editor-field-key') === activeFieldKey || el.getAttribute('data-edit-key') === activeFieldKey);
    el.classList.toggle('selected-editor-block', !!(blockMatch && (!activeFieldKey || fieldMatch)));
  });
}

function pageInspectorRows(page) {
  const fields = Object.keys(page?.editable_fields || {});
  const rows = fields.slice(0, 10).map(field => `<li>${esc(humanizeEditorToken(field))}</li>`).join('');
  return rows || '<li>No direct editable fields exposed yet</li>';
}

function selectedPageContract() {
  const {meta} = selectedInspectorMeta();
  return contractPage(activePageId || meta.page_id) || null;
}

function selectedBlockContract() {
  const {meta, page} = selectedInspectorMeta();
  return contractBlock(page, activeBlockId || meta.block_id) || null;
}

function manualBlockContextFromSelection() {
  const {fieldKey} = selectedInspectorMeta();
  const match = String(fieldKey || '').match(/^document_pages\.(\d+)\.manual_blocks\.(\d+)\./);
  if (!match) return null;
  const pageIndex = Number(match[1]);
  const blockIndex = Number(match[2]);
  const page = documentPages()[pageIndex];
  if (!page || page.page_type !== 'manual') return null;
  const block = Array.isArray(page.manual_blocks) ? page.manual_blocks[blockIndex] : null;
  if (!block) return null;
  return {page, pageIndex, block, blockIndex};
}
