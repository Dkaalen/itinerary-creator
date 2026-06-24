function attachPageEventHandlers() {
  document.querySelectorAll('[data-outline-page-id]').forEach(btn => {
    btn.addEventListener('click', event => {
      const pageId = btn.getAttribute('data-outline-page-id');
      if (event.target?.closest?.('[data-doc-page-action]')) return;
      if (pageId) scrollToPage(pageId);
    });
  });
  document.querySelectorAll('[data-doc-page-action]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.stopPropagation();
      const pageId = btn.getAttribute('data-page-id-ref');
      const action = btn.getAttribute('data-doc-page-action');
      if (!pageId) return;
      if (action === 'hide') hideDocumentPage(pageId);
      if (action === 'restore') restoreDocumentPage(pageId);
      if (action === 'duplicate') duplicateManualPage(pageId);
      if (action === 'add-after') addManualPageAfter(pageId, 'blank');
      if (action === 'move-up') moveDocumentPage(pageId, -1);
      if (action === 'move-down') moveDocumentPage(pageId, 1);
    });
  });
  let draggedPageId = '';
  document.querySelectorAll('[data-outline-row-page-id]').forEach(row => {
    row.addEventListener('dragstart', event => {
      draggedPageId = row.getAttribute('data-outline-row-page-id') || '';
      row.classList.add('dragging');
      event.dataTransfer?.setData('text/plain', draggedPageId);
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => {
      row.classList.remove('dragging');
      draggedPageId = '';
    });
    row.addEventListener('dragover', event => {
      if (!draggedPageId) return;
      event.preventDefault();
      row.classList.add('drag-over');
    });
    row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
    row.addEventListener('drop', event => {
      event.preventDefault();
      row.classList.remove('drag-over');
      const pageId = draggedPageId || event.dataTransfer?.getData('text/plain') || '';
      const targetPageId = row.getAttribute('data-outline-row-page-id') || '';
      if (!pageId || !targetPageId || pageId === targetPageId) return;
      const visible = sortedDocumentPages().filter(page => !page?.is_hidden);
      const targetIndex = visible.findIndex(page => page.page_id === targetPageId);
      if (targetIndex >= 0) moveDocumentPageToIndex(pageId, targetIndex);
    });
  });

  let draggedManualBlock = null;
  document.querySelectorAll('[data-manual-block-page-id]').forEach(blockEl => {
    blockEl.addEventListener('dragstart', event => {
      draggedManualBlock = {
        pageId: blockEl.getAttribute('data-manual-block-page-id') || '',
        index: Number(blockEl.getAttribute('data-manual-block-index') || 0),
      };
      blockEl.classList.add('dragging');
      event.dataTransfer?.setData('text/plain', JSON.stringify(draggedManualBlock));
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
    });
    blockEl.addEventListener('dragend', () => {
      blockEl.classList.remove('dragging');
      draggedManualBlock = null;
    });
    blockEl.addEventListener('dragover', event => {
      if (!draggedManualBlock) return;
      event.preventDefault();
      blockEl.classList.add('drag-over');
    });
    blockEl.addEventListener('dragleave', () => blockEl.classList.remove('drag-over'));
    blockEl.addEventListener('drop', event => {
      event.preventDefault();
      blockEl.classList.remove('drag-over');
      const targetPageId = blockEl.getAttribute('data-manual-block-page-id') || '';
      const targetIndex = Number(blockEl.getAttribute('data-manual-block-index') || 0);
      const payload = draggedManualBlock || (() => { try { return JSON.parse(event.dataTransfer?.getData('text/plain') || '{}'); } catch { return null; } })();
      if (!payload || payload.pageId !== targetPageId) return;
      moveManualBlockToIndex(targetPageId, Number(payload.index || 0), targetIndex);
    });
  });

  document.querySelectorAll('[data-warning-page-id], [data-readiness-page-id]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.stopPropagation();
      const pageId = btn.getAttribute('data-warning-page-id') || btn.getAttribute('data-readiness-page-id');
      if (pageId) scrollToPage(pageId);
    });
  });
  document.querySelectorAll('[data-page-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.getAttribute('data-page-index'));
      const action = btn.getAttribute('data-page-action');
      if (action === 'merge-up') mergeInclusionPageUp(idx);
      if (action === 'delete') deleteInclusionPage(idx);
    });
  });
  document.querySelectorAll('[data-page-id]').forEach(pageEl => {
    pageEl.addEventListener('click', event => {
      if (event.target?.closest?.('button,select,input,label,[data-editor-block-id],[data-edit-key]')) return;
      selectEditorPage(pageEl.getAttribute('data-page-id'));
    });
  });
  document.querySelectorAll('[data-editor-block-id]').forEach(el => {
    el.addEventListener('click', event => {
      if (event.target?.closest?.('button,select,input,label')) return;
      selectEditorBlockFromElement(el);
    });
  });
  document.querySelectorAll('[data-select-image-field]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      selectEditorFieldByKey(btn.getAttribute('data-select-image-field') || '');
    });
  });
}
