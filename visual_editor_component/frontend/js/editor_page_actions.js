function maxDocumentPageOrder() {
  return sortedDocumentPages().reduce((max, page) => Math.max(max, Number(page?.sort_order || 0)), 0);
}
function markDocumentPagesTouched(message = 'Page list updated') {
  markTouched('document_pages');
  notifyEditor(message);
}
function hideDocumentPage(pageId) {
  collect();
  const page = documentPageById(pageId);
  if (!page) return;
  page.is_hidden = true;
  if (activePageId === pageId) activePageId = null;
  markDocumentPagesTouched(page.page_type === 'manual' ? 'Manual page hidden' : 'Page hidden from itinerary');
  draw();
}
function restoreDocumentPage(pageId) {
  collect();
  const page = documentPageById(pageId);
  if (!page) return;
  page.is_hidden = false;
  activePageId = pageId;
  markDocumentPagesTouched('Page restored');
  draw();
  scrollToPage(pageId);
}
function activateNewManualPage(page) {
  activePageId = page.page_id;
  activeBlockId = page.manual_blocks?.[0]?.block_id || null;
  activeFieldKey = page.manual_blocks?.length ? `document_pages.${pageIndexById(page.page_id)}.manual_blocks.0.editable_fields.content_html` : `document_pages.${pageIndexById(page.page_id)}.title`;
}
function addManualPage(templateId = 'blank') {
  collect();
  const page = manualPageFromTemplate(templateId || 'blank');
  documentPages().push(page);
  activateNewManualPage(page);
  markDocumentPagesTouched(`${page.title || 'Manual page'} added`);
  draw();
  scrollToPage(page.page_id);
}
function addManualPageAfter(anchorPageId, templateId = 'blank') {
  collect();
  const page = manualPageFromTemplate(templateId || 'blank');
  documentPages().push(page);
  const allPages = sortedDocumentPages();
  const visible = allPages.filter(item => !item?.is_hidden);
  const hidden = allPages.filter(item => item?.is_hidden);
  const currentIndex = visible.findIndex(item => item.page_id === page.page_id);
  const anchorIndex = visible.findIndex(item => item.page_id === anchorPageId);
  if (currentIndex >= 0 && anchorIndex >= 0) {
    visible.splice(currentIndex, 1);
    visible.splice(Math.min(anchorIndex + 1, visible.length), 0, page);
    renumberDocumentPageOrders([...visible, ...hidden]);
  }
  activateNewManualPage(page);
  markDocumentPagesTouched(`${page.title || 'Manual page'} added`);
  draw();
  scrollToPage(page.page_id);
}
function duplicateManualPage(pageId) {
  collect();
  const original = documentPageById(pageId);
  if (!original || original.page_type !== 'manual') return;
  const clone = JSON.parse(JSON.stringify(original));
  const newId = `manual-${Date.now()}`;
  clone.page_id = newId;
  clone.title = `${original.title || 'Blank page'} copy`;
  clone.sort_order = Number(original.sort_order || maxDocumentPageOrder()) + 0.5;
  clone.is_hidden = false;
  (clone.manual_blocks || []).forEach((block, idx) => { block.block_id = `${newId}__manual-${idx + 1}`; });
  documentPages().push(clone);
  activePageId = newId;
  markDocumentPagesTouched('Manual page duplicated');
  draw();
  scrollToPage(newId);
}
function moveDocumentPage(pageId, direction) {
  collect();
  const pages = sortedDocumentPages().filter(page => !page?.is_hidden);
  const currentIndex = pages.findIndex(page => page.page_id === pageId);
  if (currentIndex < 0) return;
  const current = pages[currentIndex];
  if (!documentPageCanMove(current)) return;
  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= pages.length) return;
  const target = pages[targetIndex];
  const allPages = sortedDocumentPages();
  const currentAllIndex = allPages.findIndex(page => page.page_id === pageId);
  const targetAllIndex = allPages.findIndex(page => page.page_id === target.page_id);
  if (currentAllIndex < 0 || targetAllIndex < 0) return;
  [allPages[currentAllIndex], allPages[targetAllIndex]] = [allPages[targetAllIndex], allPages[currentAllIndex]];
  renumberDocumentPageOrders(allPages);
  activePageId = pageId;
  markDocumentPagesTouched(current.page_type === 'manual' ? 'Manual page moved' : 'Page order updated');
  draw();
  scrollToPage(pageId);
}
function moveDocumentPageToIndex(pageId, targetVisibleIndex) {
  collect();
  const allPages = sortedDocumentPages();
  const moving = allPages.find(page => page.page_id === pageId);
  if (!documentPageCanMove(moving)) return;
  const visible = allPages.filter(page => !page?.is_hidden);
  const fromVisibleIndex = visible.findIndex(page => page.page_id === pageId);
  if (fromVisibleIndex < 0) return;
  const boundedTarget = Math.max(0, Math.min(Number(targetVisibleIndex || 0), visible.length - 1));
  if (boundedTarget === fromVisibleIndex) return;
  visible.splice(fromVisibleIndex, 1);
  visible.splice(boundedTarget, 0, moving);
  const hidden = allPages.filter(page => page?.is_hidden);
  renumberDocumentPageOrders([...visible, ...hidden]);
  activePageId = pageId;
  markDocumentPagesTouched('Page order updated');
  draw();
  scrollToPage(pageId);
}
function moveDocumentPageToEdge(pageId, edge) {
  const visible = sortedDocumentPages().filter(page => !page?.is_hidden);
  moveDocumentPageToIndex(pageId, edge === 'bottom' ? visible.length - 1 : 0);
}
function moveManualPage(pageId, direction) {
  moveDocumentPage(pageId, direction);
}
function scrollToPage(pageId) {
  selectEditorPage(pageId);
  requestAnimationFrame(() => {
    const target = document.querySelector(`[data-page-id="${CSS.escape(pageId)}"]`);
    if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
    updateSelectionUi();
  });
}
function pageChrome(pageId, label, bodyHtml, options = {}) {
  const page = ensureDocumentPage(pageId, options.pageType || 'generated', label, options.sortOrder || 999, options.extras || {});
  const isHidden = !!page.is_hidden;
  const canDuplicate = page.page_type === 'manual';
  const moveControls = !isHidden ? `<button class="ghost" type="button" data-doc-page-action="move-up" data-page-id-ref="${escAttr(pageId)}" title="Move page up">↑</button><button class="ghost" type="button" data-doc-page-action="move-down" data-page-id-ref="${escAttr(pageId)}" title="Move page down">↓</button>` : '';
  const duplicateControl = canDuplicate && !isHidden ? `<button class="ghost" type="button" data-doc-page-action="duplicate" data-page-id-ref="${escAttr(pageId)}" title="Duplicate manual page">Copy</button>` : '';
  const controls = `<div class="page-controls" aria-label="Page actions"><button class="ghost" type="button" data-doc-page-action="add-after" data-page-id-ref="${escAttr(pageId)}" title="Add blank page after this page">Add page</button>${moveControls}${isHidden ? `<button class="ghost" type="button" data-doc-page-action="restore" data-page-id-ref="${escAttr(pageId)}">Restore</button>` : `<button class="danger" type="button" data-doc-page-action="hide" data-page-id-ref="${escAttr(pageId)}" title="Hide this page from the itinerary">Delete</button>`}${duplicateControl}</div>`;
  if (isHidden) return '';
  return `<div class="page-wrap ${pageLayoutClasses(page)} ${activePageId === pageId ? 'selected-page' : ''}" data-page-id="${escAttr(pageId)}"><div class="page-header-row"><div class="page-label">${esc(label)}</div>${controls}</div>${bodyHtml}</div>`;
}

function deleteInclusionPage(index) {
  collect();
  if (!model.final_pages) model.final_pages = {};
  const {pages, page} = pageObjectAt(index);
  if (!pages.length || !page) return;
  const pageText = htmlTextContent(page.html || '');
  if (pageText) {
    notifyEditor('Page still has content — move content up or clear it before removing the page.');
    return;
  }
  pages.splice(index, 1);
  model.final_pages.whats_included_pages_html = pages.length ? pages : [{html: ''}];
  markTouched('final_pages.whats_included_pages_html');
  draw();
}
function mergeInclusionPageUp(index) {
  collect();
  if (!model.final_pages) model.final_pages = {};
  const pages = Array.isArray(model.final_pages.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
  if (index <= 0 || index >= pages.length) return;
  const previous = typeof pages[index - 1] === 'string' ? {html: pages[index - 1]} : (pages[index - 1] || {html: ''});
  const current = typeof pages[index] === 'string' ? {html: pages[index]} : (pages[index] || {html: ''});
  const previousHtml = stripEditorArtifactsFromHtml(previous.html || '');
  const currentHtml = stripEditorArtifactsFromHtml(current.html || '');
  if (!htmlTextContent(currentHtml)) {
    notifyEditor('Nothing to move from this page.');
    return;
  }
  previous.html = `${previousHtml}${previousHtml && currentHtml ? '<div class="inclusion-entry-spacer"></div>' : ''}${currentHtml}`;
  pages[index - 1] = previous;
  pages.splice(index, 1);
  model.final_pages.whats_included_pages_html = pages;
  markTouched('final_pages.whats_included_pages_html');
  draw();
}
function flagSelectedIssue() {
  const el = selectedEditable();
  if (!el) return;
  const key = el.getAttribute('data-edit-key');
  const flag = {
    key,
    label: el.closest('.page-wrap')?.querySelector('.page-label')?.innerText || '',
    original: String(initialValueForKey(key) ?? ''),
    corrected: editableValue(el),
  };
  if (!Array.isArray(model.issue_flags)) model.issue_flags = [];
  model.issue_flags.push(flag);
  markTouched('issue_flags');
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = 'Issue flagged';
    note.classList.add('show');
  }
}
