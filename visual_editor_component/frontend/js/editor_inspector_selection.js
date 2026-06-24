// Right-inspector selection metadata and selected-item summary.
function selectedInspectorMeta() {
  const el = selectedEditorElement();
  const fieldKey = activeFieldKey || el?.getAttribute?.('data-editor-field-key') || el?.getAttribute?.('data-edit-key') || '';
  const meta = inferEditorBlockMetaForKey(fieldKey, el?.getAttribute?.('data-editor-field-label') || '');
  const page = contractPage(activePageId || meta.page_id) || {};
  const block = contractBlock(page, activeBlockId || meta.block_id) || {};
  return {el, fieldKey, meta, page, block};
}
function sourceRowLookup() {
  return model?.source_rows || initialPayload?.source_rows || {};
}
function renderSourceRowDetails(sourceRowIds) {
  const ids = Array.isArray(sourceRowIds) ? sourceRowIds : [];
  const lookup = sourceRowLookup();
  if (!ids.length) return '<span class="empty-source">No source rows linked</span>';
  return ids.slice(0, 8).map(id => {
    const row = lookup[String(id)] || {};
    const title = row.title || row.source_text || id;
    const meta = [row.day, row.city, row.type].filter(Boolean).join(' · ');
    const details = row.source_text || [row.title, row.details].filter(Boolean).join(' | ') || 'No source text available in payload.';
    return `<details class="source-row-detail"><summary><span class="source-chip">${esc(id)}</span><strong>${esc(String(title).slice(0, 90))}</strong></summary><div class="source-row-meta">${esc(meta || 'Source row')}</div><p>${esc(String(details).slice(0, 700))}</p></details>`;
  }).join('');
}
function renderSourceRows(sourceRowIds) {
  return renderSourceRowDetails(sourceRowIds);
}
function renderInspectorSelectionCard(fieldKey, page, block, meta) {
  const key = String(fieldKey || '');
  if (!key && !activePageId) return '';
  const isImage = fieldKindForKey(key) === 'image';
  const title = key ? inspectorFieldLabelFromKey(key, meta?.field_label || '') : (page?.title || 'Page');
  const pageLabel = page?.title || meta?.page_title || activePageId || 'Current page';
  const blockLabel = block?.title || humanizeEditorToken(block?.block_type || meta?.block_type || (isImage ? 'Image' : 'Text'));
  return `<div class="inspector-card selection-card ${isImage ? 'image' : 'text'}"><div class="inspector-kicker">Selection</div><strong>${esc(title)}</strong><dl><dt>Page</dt><dd>${esc(pageLabel)}</dd><dt>Type</dt><dd>${esc(blockLabel)}</dd></dl><div class="selection-actions"><button type="button" class="ghost mini" id="inspectorRevealSelectionBtn">Reveal on page</button><button type="button" class="ghost mini" id="inspectorClearSelectionBtn">Clear selection</button></div></div>`;
}

function revealSelectedInspectorTarget() {
  const {el, meta, page, block} = selectedInspectorMeta();
  const pageId = String(page?.page_id || meta?.page_id || activePageId || '');
  const blockId = String(block?.block_id || meta?.block_id || activeBlockId || '');
  let target = el || null;
  if (!target && blockId) target = document.querySelector(`[data-editor-block-id="${CSS.escape(blockId)}"]`);
  if (!target && pageId) target = document.querySelector(`[data-page-id="${CSS.escape(pageId)}"]`);
  if (pageId) activePageId = pageId;
  if (blockId) activeBlockId = blockId;
  if (target) {
    target.scrollIntoView({behavior: 'smooth', block: 'center'});
    target.classList.add('selection-reveal-pulse');
    setTimeout(() => target.classList.remove('selection-reveal-pulse'), 900);
    notifyEditor('Selection revealed on page');
  } else {
    notifyEditor('Select a page or block to reveal.');
  }
  updateSelectionUi();
  syncEditorFrameHeight();
}

