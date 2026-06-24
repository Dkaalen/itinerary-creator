/** Responsibility split from render.js. */
function finalTextPage(label, title, key, text, titleKey) {
  const pageId = finalPageId(key === 'important_travel_notes_text' ? 'important_travel_notes' : key);
  const isImportantNotes = key === 'important_travel_notes_text';
  const notesHtml = isImportantNotes ? (model.final_pages?.important_travel_notes_html || '') : '';
  const body = notesHtml
    ? `<div class="final-html-box readonly-premium-notes" data-editor-field-key="final_pages.${escAttr(key)}">${notesHtml}</div>`
    : editableText(text || '', `final_pages.${key}`, 'final-edit-box');
  return pageChrome(pageId, label, `<div class="a4-page final-page ${isImportantNotes ? 'important-notes-page premium-notes-page' : ''}"><div class="page-content">
    ${editableText(title, `final_pages.${titleKey || `${key}_title`}`, 'final-title', 'Final page title')}
    ${body}
  </div></div>`, {pageType: 'final_section', sortOrder: 900});
}

function listTextToHtml(text) {
  const items = String(text || '').split(/\n+/).map(item => item.trim()).filter(Boolean);
  if (!items.length) return '';
  return `<ul class="final-list">${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}

function finalHtmlPage(label, title, key, html, titleKey) {
  const sectionId = key === 'whats_not_included_html' ? 'whats_not_included' : key;
  const pageId = finalPageId(sectionId);
  return pageChrome(pageId, label, `<div class="a4-page final-page"><div class="page-content">
    ${editableText(title, `final_pages.${titleKey || `${key}_title`}`, 'final-title', 'Final page title')}
    ${editableHtml(html || '', `final_pages.${key}`, 'final-html-box')}
  </div></div>`, {pageType: 'final_section', sortOrder: 899});
}

function finalHtmlPages(label, title, key, pages, titleKey) {
  const pageId = finalPageId('whats_included');
  if (typeof pageIsHidden === 'function' && pageIsHidden(pageId)) return '';
  const cleanPages = (Array.isArray(pages) && pages.length ? pages : [{html: ''}]).map(page => {
    return typeof page === 'string' ? {html: page} : (page || {html: ''});
  });
  if (!model.final_pages) model.final_pages = {};
  model.final_pages[key] = cleanPages;
  return cleanPages.map((page, idx) => {
    const html = typeof page === 'string' ? page : (page?.html || '');
    const pageLabel = label;
    const controls = `<div class="page-controls"><button class="ghost" type="button" data-page-action="merge-up" data-page-index="${idx}" ${idx === 0 ? 'disabled' : ''}>Move content up</button><button class="danger" type="button" data-page-action="delete" data-page-index="${idx}">Remove empty page</button></div>`;
    const body = `<div class="a4-page final-page categorized-inclusions-page"><div class="page-content">
      ${editableText(title, `final_pages.${titleKey || `${key}_title`}`, 'final-title', 'Final page title')}
      ${editableHtml(html || '', `final_pages.${key}.${idx}.html`, 'final-html-box')}
    </div></div>`;
    return idx === 0 ? pageChrome(pageId, pageLabel, `<div class="page-controls local-page-controls">${controls}</div>${body}`, {pageType: 'final_section', sortOrder: 898}) : `<div class="page-wrap" data-page-id="${escAttr(pageId)}-part-${idx}"><div class="page-header-row"><div class="page-label">${esc(pageLabel)}</div>${controls}</div>${body}</div>`;
  }).join('');
}
