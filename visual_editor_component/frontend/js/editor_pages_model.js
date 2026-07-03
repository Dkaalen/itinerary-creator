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
  return !!page && page.is_hidden !== true && page.page_actions?.move !== false && page.page_type !== 'generated_day';
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
  const pageActions = {hide: true, restore: true, move: pageType !== 'generated_day', duplicate: pageType === 'manual', reset: pageType !== 'manual'};
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
      page_actions: pageActions
    }, extras || {});
    pages.push(page);
  } else {
    if (!page.title && title) page.title = title;
    if (!page.page_type && pageType) page.page_type = pageType;
    if (!page.sort_order) page.sort_order = sortOrder;
    if (!page.page_actions) page.page_actions = pageActions;
    page.page_actions = Object.assign({}, pageActions, page.page_actions || {});
    if (pageType === 'generated_day') {
      page.title = title || page.title || extras?.source_day_id || '';
      page.sort_order = sortOrder;
      page.source_day_id = extras?.source_day_id || page.source_day_id || title || '';
      page.page_actions.move = false;
    }
  }
  return page;
}


function documentPageSlug(value) {
  if (typeof editorSlug === 'function') return editorSlug(value);
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'page';
}

function dayIdentityForPage(day, index) {
  const identity = String(day?.day || day?.day_id || day?.label || '').trim();
  return identity || `Day ${index + 1}`;
}

function canonicalPageIdForDay(day, index) {
  return `day-${documentPageSlug(dayIdentityForPage(day, index))}`;
}

function generatedDayPageIds() {
  return (Array.isArray(model?.days) ? model.days : []).map((day, index) => canonicalPageIdForDay(day || {}, index));
}

function pageIdForDay(day, index) {
  const identity = dayIdentityForPage(day, index);
  const canonicalPageId = canonicalPageIdForDay(day, index);
  const page = documentPages().find(page => {
    if (page?.page_type !== 'generated_day') return false;
    if (String(page?.page_id || '') === canonicalPageId) return true;
    return String(page?.source_day_id || '').trim() === identity;
  });
  return page?.page_id || canonicalPageId;
}

function orderedPageIds(defaultIds, requestedIds) {
  const defaults = (defaultIds || []).map(pageId => String(pageId || '')).filter(Boolean);
  const ordered = (requestedIds || []).map(pageId => String(pageId || '')).filter(pageId => defaults.includes(pageId));
  defaults.forEach(pageId => {
    if (!ordered.includes(pageId)) ordered.push(pageId);
  });
  return ordered;
}

function safeDocumentPageRenderOrder(pageHtmlById = {}) {
  const availableIds = new Set(Object.keys(pageHtmlById || {}).filter(pageId => !!pageHtmlById[pageId]));
  const canonicalDayIds = generatedDayPageIds().filter(pageId => availableIds.has(pageId));
  const dayIdSet = new Set(canonicalDayIds);
  const fixedPrefix = ['cover', 'summary'].filter(pageId => availableIds.has(pageId));
  const sortedPages = sortedDocumentPages();
  const nonGeneratedIds = [];
  sortedPages.forEach(page => {
    const pageId = String(page?.page_id || '');
    if (!availableIds.has(pageId)) return;
    if (fixedPrefix.includes(pageId) || dayIdSet.has(pageId)) return;
    if (!nonGeneratedIds.includes(pageId)) nonGeneratedIds.push(pageId);
  });
  Object.keys(pageHtmlById || {}).forEach(pageId => {
    if (!availableIds.has(pageId)) return;
    if (fixedPrefix.includes(pageId) || dayIdSet.has(pageId) || nonGeneratedIds.includes(pageId)) return;
    nonGeneratedIds.push(pageId);
  });

  const canonicalOrder = [...fixedPrefix, ...canonicalDayIds, ...nonGeneratedIds];
  if (!canonicalDayIds.length) return orderedPageIds(canonicalOrder, sortedPages.map(page => page?.page_id));

  const moveableCanonicalOrder = canonicalOrder.filter(pageId => !fixedPrefix.includes(pageId));
  const moveableRequestedOrder = sortedPages.map(page => String(page?.page_id || '')).filter(pageId => !fixedPrefix.includes(pageId));
  const knownRequested = orderedPageIds(moveableCanonicalOrder, moveableRequestedOrder);
  const canonicalDayQueue = canonicalDayIds.slice();
  const usedDays = new Set();
  const merged = fixedPrefix.slice();

  knownRequested.forEach(pageId => {
    if (dayIdSet.has(pageId)) {
      const nextDayId = canonicalDayQueue.find(dayId => !usedDays.has(dayId));
      if (nextDayId) {
        merged.push(nextDayId);
        usedDays.add(nextDayId);
      }
      return;
    }
    if (!merged.includes(pageId)) merged.push(pageId);
  });

  canonicalOrder.forEach(pageId => {
    if (!merged.includes(pageId)) merged.push(pageId);
  });
  return merged.filter(pageId => availableIds.has(pageId));
}

function finalPageId(sectionId) {
  if (sectionId === 'whats_included') return 'final-whats-included';
  if (sectionId === 'whats_not_included') return 'final-whats-not-included';
  if (sectionId === 'important_travel_notes') return 'final-important-travel-notes';
  return `final-${documentPageSlug(sectionId)}`;
}
