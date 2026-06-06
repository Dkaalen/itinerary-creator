function summaryPage(summary) {
  const glance = summary?.trip_glance || {};
  const arc = summary?.journey_arc || [];
  const glanceRows = Object.keys(glance).map(key => `<div class="glance-row"><div class="glance-label">${esc(key)}</div>${editableText(glance[key], `summary.trip_glance.${key}`, 'glance-value')}</div>`).join('');
  const arcRows = arc.map((row, idx) => `<tr><td>${editableText(row.chapter, `summary.journey_arc.${idx}.chapter`, '')}</td><td>${editableText(row.days, `summary.journey_arc.${idx}.days`, '')}</td><td>${editableText(row.experience, `summary.journey_arc.${idx}.experience`, '')}</td></tr>`).join('');
  const bg = picturesAdded() ? (model.cover?.cover_background_data_uri || '') : '';
  const summaryStyle = bg ? `background-image: linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)), url('${escAttr(bg)}');` : '';
  return `<div class="page-wrap"><div class="page-label">Summary page</div><div class="a4-page summary-page" style="${summaryStyle}"><div class="page-content">
    <div class="summary-card"><div class="summary-title">Your Trip at a Glance</div>${glanceRows}</div>
    <div class="summary-card"><div class="summary-title">Your Journey Arc</div><table class="journey-table"><thead><tr><th>Chapter</th><th>Days</th><th>What You’ll Experience</th></tr></thead><tbody>${arcRows}</tbody></table></div>
  </div></div></div>`;
}
function finalTextPage(label, title, key, text) {
  return `<div class="page-wrap"><div class="page-label">${esc(label)}</div><div class="a4-page final-page"><div class="page-content">
    <div class="final-title">${esc(title)}</div>
    ${editableText(text || '', `final_pages.${key}`, 'final-edit-box')}
  </div></div></div>`;
}
function listTextToHtml(text) {
  const items = String(text || '').split(/\n+/).map(item => item.trim()).filter(Boolean);
  if (!items.length) return '';
  return `<ul class="final-list">${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}
function finalHtmlPage(label, title, key, html) {
  return `<div class="page-wrap"><div class="page-label">${esc(label)}</div><div class="a4-page final-page"><div class="page-content">
    <div class="final-title">${esc(title)}</div>
    ${editableHtml(html || '', `final_pages.${key}`, 'final-html-box')}
  </div></div></div>`;
}

function finalHtmlPages(label, title, key, pages) {
  const cleanPages = (Array.isArray(pages) && pages.length ? pages : [{html: ''}]).map(page => {
    return typeof page === 'string' ? {html: page} : (page || {html: ''});
  });
  if (!model.final_pages) model.final_pages = {};
  model.final_pages[key] = cleanPages;
  return cleanPages.map((page, idx) => {
    const html = typeof page === 'string' ? page : (page?.html || '');
    const pageLabel = label;
    const controls = `<div class="page-controls"><button class="ghost" type="button" data-page-action="merge-up" data-page-index="${idx}" ${idx === 0 ? 'disabled' : ''}>Move content up</button><button class="danger" type="button" data-page-action="delete" data-page-index="${idx}">Remove empty page</button></div>`;
    return `<div class="page-wrap"><div class="page-header-row"><div class="page-label">${esc(pageLabel)}</div>${controls}</div><div class="a4-page final-page categorized-inclusions-page"><div class="page-content">
      <div class="final-title">${esc(title)}</div>
      ${editableHtml(html || '', `final_pages.${key}.${idx}.html`, 'final-html-box')}
    </div></div></div>`;
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
  if (!model || !touchedKeys.size) {
    model = JSON.parse(JSON.stringify(initialPayload));
    if (!model.workflow) model.workflow = {pictures_added: false};
    restoreLocalDraftIfAvailable();
    if (!model.workflow) model.workflow = {pictures_added: false};
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
      <div class="toolbar-copy"><strong>${picturesAdded() ? 'Review itinerary with pictures' : 'Edit itinerary text'}</strong><span>${picturesAdded() ? 'Use the image controls on each day page, then save before exporting the final PDF.' : 'Edit directly on the document pages. Your browser keeps a local draft until you save changes.'}</span></div>
      <div class="toolbar-stack">
        <div class="toolbar-actions">
          <span id="editCount" class="stat-pill">0 manual edits pending</span>
          <span id="warningCount" class="stat-pill warn">0 warnings</span>
          <span id="savedNote" class="saved-note">Saved for now</span>
          <button class="primary" id="saveBtn" type="button">Save changes</button>
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
            <button class="ghost" id="addBulletBtn" type="button">Add bullet</button>
            <button class="ghost" id="deleteBulletBtn" type="button">Delete bullet</button>
            <button class="ghost" id="moveBulletUpBtn" type="button">Move bullet up</button>
            <button class="ghost" id="moveBulletDownBtn" type="button">Move bullet down</button>
            <button class="ghost" id="makeHeadingBtn" type="button">Make heading</button>
            <button class="ghost" id="makeNormalBtn" type="button">Normal text</button>
            <button class="ghost" id="flagIssueBtn" type="button">Flag issue</button>
          </div>
        </details>
      </div>
    </div>
    <div class="page-stack">`;
  const coverBg = picturesAdded() ? (model.cover?.cover_background_data_uri || '') : '';
  const coverInk = picturesAdded() ? (model.cover?.cover_ink || '#1f3446') : '#1f3446';
  const coverMuted = picturesAdded() ? (model.cover?.cover_muted || '#7b746c') : '#53606c';
  const coverAccent = picturesAdded() ? (model.cover?.cover_accent || '#b89555') : '#b89555';
  const coverStyle = `${coverBg ? `background-image: url('${escAttr(coverBg)}');` : ''} --cover-ink: ${escAttr(coverInk)}; --cover-muted: ${escAttr(coverMuted)}; --cover-accent: ${escAttr(coverAccent)};`;
  h += `<div class="page-wrap"><div class="page-label">Cover page</div><div class="a4-page cover-page ${picturesAdded() ? '' : 'editor-text-cover'}" style="${coverStyle}"><div class="page-content">
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
    </div></div></div>`;
  h += summaryPage(model.summary || {});
  (model.days || []).forEach((day, i) => {
    const dayNumber = String(day.day || '').replace(/^Day\s*/i, '').trim() || String(i + 1);
    h += `<div class="page-wrap"><div class="page-label">${esc(day.day)}</div><div class="a4-page day-page"><div class="page-content">
      <div class="day-kicker">DAY ${esc(dayNumber)} <span class="day-kicker-symbol">✦</span> ${editableSpan(day.city, `days.${i}.city`, 'day-kicker-city')}${day.date ? ` <span class="day-kicker-symbol">✦</span> ${esc(day.date)}` : ''}</div>
      ${editableText(day.title, `days.${i}.title`, 'day-title')}
      ${editableText(day.intro, `days.${i}.intro`, 'intro')}
      ${editableHtml(day.blocks_html || '', `days.${i}.blocks_html`, 'day-blocks')}
    </div>${imageHtml(day, i)}</div></div>`;
  });
  h += finalHtmlPages('Included', "What's included", 'whats_included_pages_html', model.final_pages?.whats_included_pages_html || [{html: model.final_pages?.whats_included_html || model.final_pages?.whats_included_text || ''}]);
  h += finalHtmlPage('Excluded', "What's not included", 'whats_not_included_html', model.final_pages?.whats_not_included_html || listTextToHtml(model.final_pages?.whats_not_included_text || ''));
  h += finalTextPage('Notes', 'Important travel notes', 'important_travel_notes_text', model.final_pages?.important_travel_notes_text || '');
  h += `</div><div class="help-strip">The PDF preview/export remains the final rendering check after saving your edits.</div></div>`;
  root.innerHTML = h;
  attachHandlers();
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateEditorStats(); Streamlit.setFrameHeight(document.body.scrollHeight + 20); });
}
