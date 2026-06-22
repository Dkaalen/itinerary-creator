function coverImageControls(key, label, image) {
  if (!picturesAdded()) return '';
  const img = image || {};
  const options = img.options || [];
  const optionHtml = options.map((opt, idx) => `<option value="${esc(opt.path)}" data-option-index="${idx}" title="${esc(opt.reason || '')}" ${opt.path === img.path ? 'selected' : ''}>${esc(opt.name)}</option>`).join('');
  return `<div class="cover-image-panel" data-cover-image-key="${esc(key)}">
    <strong>${esc(label)}</strong>
    <button type="button" data-cover-img-action="auto" data-cover-img-key="${esc(key)}">Automatic</button>
    <button type="button" class="danger" data-cover-img-action="none" data-cover-img-key="${esc(key)}">Remove</button>
    <select data-cover-img-focus="${esc(key)}">
      <option value="top" ${img.crop_focus === 'top' ? 'selected' : ''}>Sky / upper crop</option>
      <option value="center" ${img.crop_focus === 'center' ? 'selected' : ''}>Center crop</option>
      <option value="bottom" ${img.crop_focus === 'bottom' ? 'selected' : ''}>Lower crop</option>
    </select>
    <select data-cover-img-bank="${esc(key)}"><option value="">Choose replacement…</option>${optionHtml}</select>
    <button type="button" data-cover-img-action="manual" data-cover-img-key="${esc(key)}">Use selected</button>
  </div>`;
}

function summaryPage(summary) {
  const glance = summary?.trip_glance || {};
  const arc = summary?.journey_arc || [];
  const glanceRows = Object.keys(glance).map(key => `<div class="glance-row"><div class="glance-label">${esc(key)}</div>${editableText(glance[key], `summary.trip_glance.${key}`, 'glance-value')}</div>`).join('');
  const arcRows = arc.map((row, idx) => `<tr><td>${editableText(row.chapter, `summary.journey_arc.${idx}.chapter`, '')}</td><td>${editableText(row.days, `summary.journey_arc.${idx}.days`, '')}</td><td>${editableText(row.experience, `summary.journey_arc.${idx}.experience`, '')}</td></tr>`).join('');
  const bg = picturesAdded() ? (model.cover?.summary_image?.data_uri || model.cover?.cover_background_data_uri || '') : '';
  const summaryFocus = model.cover?.summary_image?.crop_focus || 'top';
  const summaryStyle = bg ? `background-image: linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)), url('${escAttr(bg)}'); background-position: center center, ${focusPos(summaryFocus)};` : '';
  return `<div class="a4-page summary-page" style="${summaryStyle}"><div class="page-content">
    ${coverImageControls('summary_image', 'Page 2 background image', model.cover?.summary_image)}
    <div class="summary-card"><div class="summary-title">Your Trip at a Glance</div>${glanceRows}</div>
    <div class="summary-card"><div class="summary-title">Your Journey Arc</div><table class="journey-table"><thead><tr><th>Chapter</th><th>Days</th><th>What You’ll Experience</th></tr></thead><tbody>${arcRows}</tbody></table></div>
  </div></div>`;
}
function finalTextPage(label, title, key, text) {
  const pageId = finalPageId(key === 'important_travel_notes_text' ? 'important_travel_notes' : key);
  return pageChrome(pageId, label, `<div class="a4-page final-page"><div class="page-content">
    <div class="final-title">${esc(title)}</div>
    ${editableText(text || '', `final_pages.${key}`, 'final-edit-box')}
  </div></div>`, {pageType: 'final_section', sortOrder: 900});
}
function listTextToHtml(text) {
  const items = String(text || '').split(/\n+/).map(item => item.trim()).filter(Boolean);
  if (!items.length) return '';
  return `<ul class="final-list">${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}
function finalHtmlPage(label, title, key, html) {
  const sectionId = key === 'whats_not_included_html' ? 'whats_not_included' : key;
  const pageId = finalPageId(sectionId);
  return pageChrome(pageId, label, `<div class="a4-page final-page"><div class="page-content">
    <div class="final-title">${esc(title)}</div>
    ${editableHtml(html || '', `final_pages.${key}`, 'final-html-box')}
  </div></div>`, {pageType: 'final_section', sortOrder: 899});
}

function finalHtmlPages(label, title, key, pages) {
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
      <div class="final-title">${esc(title)}</div>
      ${editableHtml(html || '', `final_pages.${key}.${idx}.html`, 'final-html-box')}
    </div></div>`;
    return idx === 0 ? pageChrome(pageId, pageLabel, `<div class="page-controls local-page-controls">${controls}</div>${body}`, {pageType: 'final_section', sortOrder: 898}) : `<div class="page-wrap" data-page-id="${escAttr(pageId)}-part-${idx}"><div class="page-header-row"><div class="page-label">${esc(pageLabel)}</div>${controls}</div>${body}</div>`;
  }).join('');
}

function warningLocationLabel(warning) {
  const text = String(warning?.excerpt || warning?.message || '');
  const code = String(warning?.code || 'warning');
  if (warning?.page_label) return String(warning.page_label);
  const dayMatch = text.match(/\bDay\s+\d+\b/i);
  if (dayMatch) return dayMatch[0];
  for (const day of (model.days || [])) {
    const label = String(day.day || '');
    const haystack = [day.title, day.intro, day.blocks_html, day.city].map(v => String(v || '')).join(' ');
    if (text && haystack.includes(text.slice(0, Math.min(40, text.length)))) return label || 'Day page';
  }
  if (/included|exclusion|commercial|self-arranged/i.test(text) || /inclusion|exclusion/i.test(code)) return 'Final pages';
  return 'Review item';
}
function warningExplanation(warning) {
  const code = String(warning?.code || 'warning');
  if (code.includes('source_signal') || code.includes('source')) return 'Source detail may have been lost or renamed. Compare the page with the input row.';
  if (code.includes('aurora')) return 'Aurora appears in client text. Keep it only when it is part of the real supplier/product name.';
  if (code.includes('time')) return 'Time wording may contain supplier note text or an unusual time. Verify before export.';
  if (code.includes('image')) return 'Image review needs attention for this destination/page.';
  if (code.includes('optional')) return 'Optional or excluded wording may need review so it does not look confirmed.';
  return 'Review this item before exporting the final PDF.';
}
function warningPanelHtml() {
  const warnings = Array.isArray(model.client_output_warnings) ? model.client_output_warnings : [];
  if (!warnings.length) return '';
  const rows = warnings.slice(0, 12).map((warning, idx) => {
    const location = warningLocationLabel(warning);
    const excerpt = String(warning?.excerpt || warning?.message || warning?.code || 'Review warning');
    return `<li><strong>${esc(location)}</strong><span>${esc(warningExplanation(warning))}</span><em>${esc(excerpt)}</em></li>`;
  }).join('');
  const hidden = warnings.length > 12 ? `<div class="warning-panel-more">${warnings.length - 12} more warning(s) hidden here. Use the page highlights and final PDF check as well.</div>` : '';
  return `<details class="warning-panel" ${warnings.length <= 8 ? 'open' : ''}><summary>${warnings.length} warning(s) to review</summary><ul>${rows}</ul>${hidden}</details>`;
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
function renderDocumentOutline() {
  const pages = typeof sortedDocumentPages === 'function' ? sortedDocumentPages() : (Array.isArray(model.document_pages) ? model.document_pages : []);
  const rows = pages.map(page => {
    const pageId = String(page?.page_id || '');
    const title = String(page?.title || pageId || 'Untitled page');
    const hidden = !!page?.is_hidden;
    const isManual = page?.page_type === 'manual';
    const action = hidden
      ? `<button type="button" data-doc-page-action="restore" data-page-id-ref="${escAttr(pageId)}">Restore</button>`
      : `<button type="button" data-doc-page-action="hide" data-page-id-ref="${escAttr(pageId)}">Delete</button>`;
    const manualActions = isManual && !hidden
      ? `<button type="button" data-doc-page-action="move-up" data-page-id-ref="${escAttr(pageId)}">↑</button><button type="button" data-doc-page-action="move-down" data-page-id-ref="${escAttr(pageId)}">↓</button><button type="button" data-doc-page-action="duplicate" data-page-id-ref="${escAttr(pageId)}">Copy</button>`
      : '';
    return `<li class="outline-row ${hidden ? 'hidden' : ''} ${activePageId === pageId ? 'active' : ''}" data-outline-page-id="${escAttr(pageId)}">
      <button class="outline-jump" type="button" data-outline-page-id="${escAttr(pageId)}"><span>${esc(title)}</span><em>${esc(pageTypeLabel(page))}${hidden ? ' · Hidden' : ''}</em></button>
      <div class="outline-actions">${action}${manualActions}</div>
    </li>`;
  }).join('');
  return `<aside class="document-outline" aria-label="Document pages">
    <div class="outline-title"><strong>Pages</strong><span>${pages.length} total</span></div>
    <button class="primary outline-add" id="addManualPageBtn" type="button">Add blank page</button>
    <ul>${rows}</ul>
    <p class="outline-hint">Generated pages are hidden when deleted and can be restored. Manual pages stay fully editable.</p>
  </aside>`;
}
function renderManualPages() {
  if (typeof sortedDocumentPages !== 'function') return '';
  return sortedDocumentPages().filter(page => page?.page_type === 'manual').map((page, pageIndex) => {
    const realIndex = typeof pageIndexById === 'function' ? pageIndexById(page.page_id) : pageIndex;
    const blocks = Array.isArray(page.manual_blocks) && page.manual_blocks.length
      ? page.manual_blocks
      : [{editable_fields: {content_html: '<div class="body-text">New page text</div>'}}];
    const body = blocks.map((block, blockIndex) => {
      const html = block?.editable_fields?.content_html || '';
      return editableHtml(html, `document_pages.${realIndex}.manual_blocks.${blockIndex}.editable_fields.content_html`, 'manual-page-edit-box');
    }).join('');
    return pageChrome(page.page_id, page.title || 'Blank page', `<div class="a4-page manual-page"><div class="page-content"><div class="final-title">${editableText(page.title || 'Blank page', `document_pages.${realIndex}.title`, 'manual-page-title')}</div>${body}</div></div>`, {pageType: 'manual', sortOrder: page.sort_order || 999});
  }).join('');
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
  const root = document.getElementById('root');
  let h = `<div class="editor-shell">
    <div class="editor-toolbar">
      <div class="toolbar-copy"><strong>${picturesAdded() ? 'Review itinerary with pictures' : 'Edit itinerary text'}</strong><span>${picturesAdded() ? 'Use the image controls on each day page, then save before exporting the final PDF.' : 'Edit directly on the document pages. Changes autosave quietly while you work.'}</span></div>
      <div class="toolbar-stack">
        <div class="toolbar-actions">
          <span id="editCount" class="stat-pill">0 manual edits pending</span>
          <span id="warningCount" class="stat-pill warn">0 warnings</span>
          <span id="savedNote" class="saved-note">Autosave ready</span>
          <button class="primary" id="saveBtn" type="button">Save changes</button>
        </div>
        <div class="toolbar-tools style-tools">
          <select id="textStylePreset" aria-label="Text style preset">${controlledPresetOptionsHtml('text_styles', 'Text style')}</select>
          <select id="colorPreset" aria-label="Color preset">${controlledPresetOptionsHtml('colors', 'Color')}</select>
          <button class="ghost" id="addNoteBlockBtn" type="button">Add note block</button>
          <button class="ghost" id="addDividerBtn" type="button">Add divider</button>
          <button class="ghost" id="compactSpacingBtn" type="button">Compact spacing</button>
          <button class="ghost" id="normalSpacingBtn" type="button">Normal spacing</button>
        </div>
        <details class="advanced-tools">
          <summary>Advanced tools</summary>
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
      ${warningPanelHtml()}
    </div>
    <div class="editor-workspace">
      ${renderDocumentOutline()}
      <div class="page-stack">`;
  const coverBg = picturesAdded() ? (model.cover?.cover_image?.data_uri || model.cover?.cover_background_data_uri || '') : '';
  const coverInk = picturesAdded() ? (model.cover?.cover_ink || '#1f3446') : '#1f3446';
  const coverMuted = picturesAdded() ? (model.cover?.cover_muted || '#7b746c') : '#53606c';
  const coverAccent = picturesAdded() ? (model.cover?.cover_accent || '#b89555') : '#b89555';
  const coverFocus = model.cover?.cover_image?.crop_focus || 'top';
  const coverStyle = `${coverBg ? `background-image: url('${escAttr(coverBg)}'); background-position: ${focusPos(coverFocus)};` : ''} --cover-ink: ${escAttr(coverInk)}; --cover-muted: ${escAttr(coverMuted)}; --cover-accent: ${escAttr(coverAccent)};`;
  h += pageChrome('cover', 'Cover page', `<div class="a4-page cover-page ${picturesAdded() ? '' : 'editor-text-cover'}" style="${coverStyle}"><div class="page-content">
      ${coverImageControls('cover_image', 'Front cover image', model.cover?.cover_image)}
      <div class="cover-main">
        <div class="cover-emblem" aria-hidden="true"></div>
        ${editableText(model.cover?.cover_kicker || 'Travel Itinerary', 'cover.cover_kicker', 'cover-kicker')}
        ${editableText(model.cover?.trip_title, 'cover.trip_title', 'cover-title')}
        ${editableText(model.cover?.trip_subtitle, 'cover.trip_subtitle', 'cover-subtitle')}
        ${model.cover?.trip_dates ? editableText(model.cover.trip_dates, 'cover.trip_dates', 'cover-dates') : ''}
        <div class="cover-rule"></div>
        <div class="cover-destination-card">
          <div class="cover-destination-label">Route</div>
          ${editableRoute(model.cover?.destinations_line, 'cover.destinations_line', 'cover-destinations')}
        </div>
      </div>
    </div></div>`, {pageType: 'cover', sortOrder: 1});
  h += pageChrome('summary', 'Summary page', summaryPage(model.summary || {}), {pageType: 'summary', sortOrder: 2});
  (model.days || []).forEach((day, i) => {
    const dayNumber = String(day.day || '').replace(/^Day\s*/i, '').trim() || String(i + 1);
    const pageId = pageIdForDay(day, i);
    h += pageChrome(pageId, day.day || `Day ${i + 1}`, `<div class="a4-page day-page"><div class="page-content">
      <div class="day-kicker">DAY ${esc(dayNumber)} <span class="day-kicker-symbol">✦</span> ${editableSpan(day.city, `days.${i}.city`, 'day-kicker-city')}${day.date ? ` <span class="day-kicker-symbol">✦</span> ${esc(day.date)}` : ''}</div>
      ${editableText(day.title, `days.${i}.title`, 'day-title')}
      ${editableText(day.intro, `days.${i}.intro`, 'intro')}
      ${editableHtml(day.blocks_html || '', `days.${i}.blocks_html`, 'day-blocks')}
    </div>${imageHtml(day, i)}</div>`, {pageType: 'generated_day', sortOrder: i + 3, extras: {source_day_id: String(day.day || day.label || '')}});
  });
  h += finalHtmlPages('Included', "What's included", 'whats_included_pages_html', model.final_pages?.whats_included_pages_html || [{html: model.final_pages?.whats_included_html || model.final_pages?.whats_included_text || ''}]);
  h += finalHtmlPage('Excluded', "What's not included", 'whats_not_included_html', model.final_pages?.whats_not_included_html || listTextToHtml(model.final_pages?.whats_not_included_text || ''));
  h += finalTextPage('Notes', 'Important travel notes', 'important_travel_notes_text', model.final_pages?.important_travel_notes_text || '');
  h += renderManualPages();
  h += `</div></div><div class="help-strip">The PDF preview/export remains the final rendering check after saving your edits.</div></div>`;
  root.innerHTML = h;
  attachHandlers();
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateEditorStats(); Streamlit.setFrameHeight(document.body.scrollHeight + 20); });
}
