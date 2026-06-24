/** Responsibility split from render.js. */
function pageTypeLabel(page) {
  const type = String(page?.page_type || 'page');
  if (type === 'generated_day') return 'Day';
  if (type === 'final_section') return 'Final';
  if (type === 'manual') return 'Manual';
  if (type === 'cover') return 'Cover';
  if (type === 'summary') return 'Summary';
  return 'Page';
}

function editorStudioStats() {
  const pages = typeof sortedDocumentPages === 'function' ? sortedDocumentPages() : (Array.isArray(model?.document_pages) ? model.document_pages : []);
  const visible = pages.filter(page => !page?.is_hidden).length;
  const hidden = pages.filter(page => page?.is_hidden).length;
  const manual = pages.filter(page => page?.page_type === 'manual' && !page?.is_hidden).length;
  const dirtyPages = pages.filter(page => pageHasDirtyEdits(page?.page_id)).length;
  const selection = activeBlockId ? 'Block selected' : (activePageId ? 'Page selected' : 'No selection');
  return {visible, hidden, manual, dirtyPages, selection};
}

function studioStatusStripHtml() {
  const stats = editorStudioStats();
  const summary = `${stats.visible} visible · ${stats.selection} · ${touchedKeys.size} unsaved`;
  return `<details class="studio-status-panel">
    <summary><strong>Document status</strong><span>${esc(summary)}</span></summary>
    <div class="studio-status-strip" aria-label="Editor document status">
      <span class="studio-metric"><b>${esc(stats.visible)}</b><small>Visible pages</small></span>
      <span class="studio-metric ${stats.hidden ? 'review' : ''}"><b>${esc(stats.hidden)}</b><small>Hidden</small></span>
      <span class="studio-metric"><b>${esc(stats.manual)}</b><small>Manual pages</small></span>
      <span class="studio-metric ${stats.dirtyPages ? 'review' : ''}"><b id="studioDirtyPagesMetric">${esc(stats.dirtyPages)}</b><small>Dirty pages</small></span>
      <span class="studio-metric selection"><b id="studioSelectionMetric">${esc(stats.selection)}</b><small>Selection</small></span>
      <span class="studio-metric"><b id="studioEditsMetric">${esc(touchedKeys.size)}</b><small>Unsaved edits</small></span>
    </div>
  </details>`;
}

function renderDocumentOutline() {
  const pages = typeof sortedDocumentPages === 'function' ? sortedDocumentPages() : (Array.isArray(model.document_pages) ? model.document_pages : []);
  const rows = pages.map(page => {
    const pageId = String(page?.page_id || '');
    const title = String(page?.title || pageId || 'Untitled page');
    const hidden = !!page?.is_hidden;
    const dirty = pageHasDirtyEdits(pageId);
    const badges = `${hidden ? '<b class="outline-status hidden">Hidden</b>' : ''}${dirty ? '<b class="outline-status dirty">Unsaved</b>' : ''}`;
    return `<li class="outline-row ${hidden ? 'hidden' : ''} ${dirty ? 'dirty' : ''} ${activePageId === pageId ? 'active' : ''}" data-outline-page-id="${escAttr(pageId)}" data-outline-row-page-id="${escAttr(pageId)}">
      <button class="outline-jump" type="button" data-outline-page-id="${escAttr(pageId)}"><span>${esc(title)}</span><em>${esc(pageTypeLabel(page))}</em>${badges ? `<span class="outline-status-row">${badges}</span>` : ''}</button>
    </li>`;
  }).join('');
  return `<aside class="document-outline" aria-label="Document pages">
    <div class="outline-title"><strong>Pages</strong><span>${pages.length} total</span></div>
    <ul>${rows}</ul>
  </aside>`;
}

function pagesMenuHtml() {
  return `<details class="pages-menu">
    <summary>Pages</summary>
    ${renderDocumentOutline()}
  </details>`;
}
