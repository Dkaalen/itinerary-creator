/** Responsibility split from editor_document_model.js. */
function documentPages() {
  if (!Array.isArray(model.document_pages)) model.document_pages = [];
  return model.document_pages;
}

function sortedDocumentPages() {
  return documentPages().slice().sort((a, b) => Number(a?.sort_order || 0) - Number(b?.sort_order || 0));
}

function renumberDocumentPageOrders(orderedPages = null) {
  const ordered = orderedPages || sortedDocumentPages();
  ordered.forEach((page, index) => {
    if (page) page.sort_order = index + 1;
  });
  return ordered;
}

function documentPageCanMove(page) {
  return !!page && page.is_hidden !== true;
}

function documentPageCanDuplicate(page) {
  return !!page && page.page_type === 'manual' && page.is_hidden !== true;
}

function documentPageById(pageId) {
  return documentPages().find(page => String(page?.page_id || '') === String(pageId || '')) || null;
}

function pageIndexById(pageId) {
  return documentPages().findIndex(page => String(page?.page_id || '') === String(pageId || ''));
}

function pageIsHidden(pageId) {
  return !!documentPageById(pageId)?.is_hidden;
}

function ensureDocumentPage(pageId, pageType, title, sortOrder, extras = {}) {
  const pages = documentPages();
  let page = documentPageById(pageId);
  if (!page) {
    page = Object.assign({
      page_id: pageId,
      page_type: pageType,
      title,
      sort_order: sortOrder,
      is_hidden: false,
      generated_blocks: [],
      manual_blocks: [],
      editable_fields: {},
      style_overrides: {},
      page_overrides: {},
      page_actions: {hide: true, restore: true, move: true, duplicate: pageType === 'manual', reset: pageType !== 'manual'}
    }, extras || {});
    pages.push(page);
  } else {
    if (!page.title && title) page.title = title;
    if (!page.page_type && pageType) page.page_type = pageType;
    if (!page.sort_order) page.sort_order = sortOrder;
    if (!page.page_actions) page.page_actions = {hide: true, restore: true, move: true, duplicate: pageType === 'manual', reset: pageType !== 'manual'};
  }
  return page;
}

function pageIdForDay(day, index) {
  const identity = String(day?.day || day?.day_id || day?.label || '').trim();
  const page = documentPages().find(page => {
    if (page?.page_type !== 'generated_day') return false;
    if (identity && String(page?.source_day_id || '') === identity) return true;
    if (identity && String(page?.title || '') === identity) return true;
    return Number(page?.sort_order || 0) === index + 3;
  });
  return page?.page_id || `day-${editorSlug(identity || `Day ${index + 1}`)}`;
}

function finalPageId(sectionId) {
  if (sectionId === 'whats_included') return 'final-whats-included';
  if (sectionId === 'whats_not_included') return 'final-whats-not-included';
  if (sectionId === 'important_travel_notes') return 'final-important-travel-notes';
  return `final-${editorSlug(sectionId)}`;
}
