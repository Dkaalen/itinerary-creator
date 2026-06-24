/** Responsibility split from render.js. */
function renderManualPageHtml(page, fallbackIndex = 0) {
  if (!page || page.page_type !== 'manual') return '';
  const realIndex = typeof pageIndexById === 'function' ? pageIndexById(page.page_id) : fallbackIndex;
    const blocks = Array.isArray(page.manual_blocks) && page.manual_blocks.length
      ? page.manual_blocks
      : [{editable_fields: {content_html: '<div class="body-text">New page text</div>'}}];
    const body = blocks.map((block, blockIndex) => {
      const html = block?.editable_fields?.content_html || '';
      const blockId = block?.block_id || `${page.page_id}__manual-${blockIndex + 1}`;
      const label = block?.title || humanizeEditorToken(block?.block_type || 'Manual block');
      return `<div class="manual-block-shell ${blockLayoutClasses(block)}" draggable="true" data-manual-block-page-id="${escAttr(page.page_id)}" data-manual-block-index="${blockIndex}" data-editor-page-id="${escAttr(page.page_id)}" data-editor-block-id="${escAttr(blockId)}" data-editor-block-type="${escAttr(block?.block_type || 'manual_text')}" data-editor-field-key="document_pages.${realIndex}.manual_blocks.${blockIndex}.editable_fields.content_html" data-editor-field-label="${escAttr(label)}"><div class="manual-block-drag-handle" aria-hidden="true" title="Drag block to reorder">⋮⋮</div>${editableHtml(html, `document_pages.${realIndex}.manual_blocks.${blockIndex}.editable_fields.content_html`, 'manual-page-edit-box', label)}</div>`;
    }).join('');
    return pageChrome(page.page_id, page.title || 'Blank page', `<div class="a4-page manual-page"><div class="page-content"><div class="final-title">${editableText(page.title || 'Blank page', `document_pages.${realIndex}.title`, 'manual-page-title')}</div>${body}</div></div>`, {pageType: 'manual', sortOrder: page.sort_order || 999});
}

function renderManualPages() {
  if (typeof sortedDocumentPages !== 'function') return '';
  return sortedDocumentPages().filter(page => page?.page_type === 'manual').map((page, pageIndex) => renderManualPageHtml(page, pageIndex)).join('');
}
