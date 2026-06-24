function summaryPage(summary) {
  const glance = summary?.trip_glance || {};
  const arc = summary?.journey_arc || [];
  const columns = summary?.journey_arc_columns || {};
  const glanceRows = Object.keys(glance).map(key => `<div class="glance-row"><div class="glance-label">${esc(key)}</div>${editableText(glance[key], `summary.trip_glance.${key}`, 'glance-value', `Trip glance ${key}`)}</div>`).join('');
  const arcRows = arc.map((row, idx) => `<tr><td>${editableText(row.chapter, `summary.journey_arc.${idx}.chapter`, '')}</td><td>${editableText(row.days, `summary.journey_arc.${idx}.days`, '')}</td><td>${editableText(row.experience, `summary.journey_arc.${idx}.experience`, '')}</td></tr>`).join('');
  const bg = picturesAdded() ? (model.cover?.summary_image?.data_uri || model.cover?.cover_background_data_uri || '') : '';
  const summaryFocus = model.cover?.summary_image?.crop_focus || 'top';
  const summaryStyle = bg ? `background-image: linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)), url('${escAttr(bg)}'); background-position: center center, ${focusPos(summaryFocus)};` : '';
  return `<div class="a4-page summary-page" style="${summaryStyle}"><div class="page-content">
    ${coverImageControls('summary_image', 'Page 2 background image', model.cover?.summary_image)}
    <div class="summary-card">${editableText(summary?.trip_glance_title || 'Your Trip at a Glance', 'summary.trip_glance_title', 'summary-title', 'Trip glance title')}${glanceRows}</div>
    <div class="summary-card">${editableText(summary?.journey_arc_title || 'Your Journey Arc', 'summary.journey_arc_title', 'summary-title', 'Journey arc title')}<table class="journey-table"><thead><tr><th>${editableSpan(columns.chapter || 'Chapter', 'summary.journey_arc_columns.chapter', 'table-header-edit', 'Chapter column')}</th><th>${editableSpan(columns.days || 'Days', 'summary.journey_arc_columns.days', 'table-header-edit', 'Days column')}</th><th>${editableSpan(columns.experience || 'What You’ll Experience', 'summary.journey_arc_columns.experience', 'table-header-edit', 'Experience column')}</th></tr></thead><tbody>${arcRows}</tbody></table></div>
  </div></div>`;
}
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

function render(payload, commitNonce = null) {
  const shouldCommitPendingEdits = !!(commitNonce && commitNonce !== lastCommitNonce);
  if (shouldCommitPendingEdits) {
    lastCommitNonce = commitNonce;
    // Streamlit asks for this when the user clicks Create PDF. Do not redraw
    // from the server payload first, because that would overwrite unsaved
    // browser-side text edits before collect() can read them.
    setTimeout(() => saveChanges(commitNonce), 0);
    return;
  }
  initialPayload = JSON.parse(JSON.stringify(payload || {cover:{},summary:{},days:[],final_pages:{}}));
  hydrateSaveStateFromPayload(initialPayload);
  const incomingPicturesAdded = !!initialPayload?.workflow?.pictures_added;
  const currentPicturesAdded = !!model?.workflow?.pictures_added;
  const workflowPromotedToPictures = incomingPicturesAdded && !currentPicturesAdded;
  if (!model || !touchedKeys.size || workflowPromotedToPictures) {
    model = JSON.parse(JSON.stringify(initialPayload));
    if (!model.workflow) model.workflow = {pictures_added: false};
    restoreLocalDraftIfAvailable();
    if (!model.workflow) model.workflow = {pictures_added: false};
    if (incomingPicturesAdded) model.workflow.pictures_added = true;
    uploadedImages = {};
    touchedKeys = new Set();
  }
  lastSavedPayload = '';
  draw();
  if (restoredLocalDraftPendingSave) {
    setTimeout(saveRestoredLocalDraftToServer, 0);
  }
}
function draw() {
  captureEditorScrollState('draw');
  const root = document.getElementById('root');
  let h = `<div class="editor-shell">
    <div class="editor-toolbar">
      <div class="toolbar-main">
        <div class="toolbar-copy compact"><strong>Editor</strong><span>${picturesAdded() ? 'Pictures added · review pages and save when done.' : 'Edit on the page · Changes autosave quietly while you work'}</span><span class="toolbar-legacy-label">${picturesAdded() ? 'Review itinerary with pictures · hover an image to edit it on the canvas' : 'Edit itinerary text · use the formatting inspector for font, size, and color'}</span></div>
      </div>
      <div class="toolbar-stack">
        <div class="toolbar-actions">
          <span id="editCount" class="stat-pill">0 manual edits pending</span>
          <span id="warningCount" class="stat-pill warn">0 warnings</span>
          ${pdfReadinessBadgeHtml()}
          <span id="savedNote" class="saved-note">Autosave ready</span>
          ${pagesMenuHtml()}
          <button class="primary" id="saveBtn" type="button">Save changes</button>
        </div>
        ${saveRecoveryPanelHtml()}
        <details class="advanced-tools">
          <summary>Advanced tools</summary>
          ${studioStatusStripHtml()}
          <div class="toolbar-tools">
            <button class="ghost" id="undoBtn" type="button">Undo</button>
            <button class="ghost" id="resetBlockBtn" type="button">Reset section</button>
            <button class="ghost" id="resetBtn" type="button">Reset draft</button>
            <input id="findText" type="text" placeholder="Find text">
            <input id="replaceText" type="text" placeholder="Replace with">
            <button class="ghost" id="replaceBtn" type="button">Replace all</button>
            <button class="ghost" id="flagIssueBtn" type="button">Flag issue</button>
          </div>
        </details>
      </div>
      ${reviewCenterHtml()}
    </div>
    <div class="editor-workspace">
      <div class="page-stack">`;
  const coverBg = picturesAdded() ? (model.cover?.cover_image?.data_uri || model.cover?.cover_background_data_uri || '') : '';
  const coverInk = picturesAdded() ? (model.cover?.cover_ink || '#1f3446') : '#1f3446';
  const coverMuted = picturesAdded() ? (model.cover?.cover_muted || '#7b746c') : '#53606c';
  const coverAccent = picturesAdded() ? (model.cover?.cover_accent || '#b89555') : '#b89555';
  const coverFocus = model.cover?.cover_image?.crop_focus || 'top';
  const coverStyle = `${coverBg ? `background-image: url('${escAttr(coverBg)}'); background-position: ${focusPos(coverFocus)};` : ''} --cover-ink: ${escAttr(coverInk)}; --cover-muted: ${escAttr(coverMuted)}; --cover-accent: ${escAttr(coverAccent)};`;
  const pageHtmlById = {};
  const addPageHtml = (pageId, html) => { pageHtmlById[pageId] = (pageHtmlById[pageId] || '') + (html || ''); };
  addPageHtml('cover', pageChrome('cover', 'Cover page', `<div class="a4-page cover-page ${picturesAdded() ? '' : 'editor-text-cover'}" style="${coverStyle}"><div class="page-content">
      ${coverImageControls('cover_image', 'Front cover image', model.cover?.cover_image)}
      <div class="cover-main">
        <div class="cover-emblem" aria-hidden="true"></div>
        ${editableText(model.cover?.cover_kicker || 'Travel Itinerary', 'cover.cover_kicker', 'cover-kicker')}
        ${editableText(model.cover?.trip_title, 'cover.trip_title', 'cover-title')}
        ${editableText(model.cover?.trip_subtitle, 'cover.trip_subtitle', 'cover-subtitle')}
        ${model.cover?.trip_dates ? editableText(model.cover.trip_dates, 'cover.trip_dates', 'cover-dates') : ''}
        <div class="cover-rule"></div>
        <div class="cover-destination-card">
          ${editableText(model.cover?.route_label || 'Route', 'cover.route_label', 'cover-destination-label', 'Route label')}
          ${editableRoute(model.cover?.destinations_line, 'cover.destinations_line', 'cover-destinations')}
        </div>
      </div>
    </div></div>`, {pageType: 'cover', sortOrder: 1}));
  addPageHtml('summary', pageChrome('summary', 'Summary page', summaryPage(model.summary || {}), {pageType: 'summary', sortOrder: 2}));
  (model.days || []).forEach((day, i) => {
    const dayNumber = String(day.day || '').replace(/^Day\s*/i, '').trim() || String(i + 1);
    const pageId = pageIdForDay(day, i);
    addPageHtml(pageId, pageChrome(pageId, day.day || `Day ${i + 1}`, `<div class="a4-page day-page"><div class="page-content">
      <div class="day-kicker">DAY ${esc(dayNumber)} <span class="day-kicker-symbol">✦</span> ${editableSpan(day.city, `days.${i}.city`, 'day-kicker-city')} <span class="day-kicker-symbol">✦</span> ${editableSpan(day.date || '', `days.${i}.date`, 'day-kicker-date', 'Date')}</div>
      ${editableText(day.title, `days.${i}.title`, 'day-title')}
      ${editableText(day.intro, `days.${i}.intro`, 'intro')}
      ${editableHtml(day.blocks_html || '', `days.${i}.blocks_html`, 'day-blocks')}
    </div>${imageHtml(day, i)}</div>`, {pageType: 'generated_day', sortOrder: i + 3, extras: {source_day_id: String(day.day || day.label || '')}}));
  });
  addPageHtml(finalPageId('whats_included'), finalHtmlPages('Included', model.final_pages?.whats_included_title || "What's included", 'whats_included_pages_html', model.final_pages?.whats_included_pages_html || [{html: model.final_pages?.whats_included_html || model.final_pages?.whats_included_text || ''}], 'whats_included_title'));
  addPageHtml(finalPageId('whats_not_included'), finalHtmlPage('Excluded', model.final_pages?.whats_not_included_title || "What's not included", 'whats_not_included_html', model.final_pages?.whats_not_included_html || listTextToHtml(model.final_pages?.whats_not_included_text || ''), 'whats_not_included_title'));
  addPageHtml(finalPageId('important_travel_notes'), finalTextPage('Notes', model.final_pages?.important_travel_notes_title || 'Important travel notes', 'important_travel_notes_text', model.final_pages?.important_travel_notes_text || '', 'important_travel_notes_title'));
  sortedDocumentPages().filter(page => page?.page_type === 'manual').forEach(page => {
    const html = renderManualPageHtml(page);
    if (html) addPageHtml(page.page_id, html);
  });
  const renderedPageIds = new Set();
  sortedDocumentPages().forEach(page => {
    const pageId = String(page?.page_id || '');
    if (pageHtmlById[pageId]) {
      h += pageHtmlById[pageId];
      renderedPageIds.add(pageId);
    }
  });
  Object.keys(pageHtmlById).forEach(pageId => {
    if (!renderedPageIds.has(pageId)) h += pageHtmlById[pageId];
  });
  h += `</div>${renderRightInspector()}</div><div class="help-strip">The PDF preview/export remains the final rendering check after saving your edits.</div></div>`;
  root.innerHTML = h;
  attachHandlers();
  restoreEditorScrollState();
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateEditorStats(); syncEditorFrameHeight(); restoreEditorScrollState(); });
}
