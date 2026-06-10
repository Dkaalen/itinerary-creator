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
        <details class="advanced-tools">
          <summary>Advanced tools</summary>
          <div class="toolbar-tools">
            <button class="ghost" id="undoBtn" type="button">Undo</button>
            <button class="ghost" id="resetBlockBtn" type="button">Reset section</button>
            <button class="ghost" id="resetBtn" type="button">Reset draft</button>
            <select id="textStylePreset" aria-label="Text style preset">
              <option value="">Text style</option>
              <option value="normal">Normal text</option>
              <option value="small_note">Small note</option>
              <option value="large_text">Large text</option>
              <option value="heading">Heading</option>
              <option value="subheading">Subheading</option>
              <option value="muted_text">Muted text</option>
              <option value="accent_text">Accent text</option>
            </select>
            <select id="colorPreset" aria-label="Color preset">
              <option value="">Color</option>
              <option value="default">Default</option>
              <option value="muted_grey">Muted grey</option>
              <option value="accent_gold">Accent gold</option>
              <option value="warning">Warning / important</option>
              <option value="soft_highlight">Soft highlight</option>
            </select>
            <button class="ghost" id="addNoteBlockBtn" type="button">Add note block</button>
            <button class="ghost" id="addDividerBtn" type="button">Add divider</button>
            <button class="ghost" id="compactSpacingBtn" type="button">Compact spacing</button>
            <button class="ghost" id="normalSpacingBtn" type="button">Normal spacing</button>
            <input id="findText" type="text" placeholder="Find text">
            <input id="replaceText" type="text" placeholder="Replace with">
            <button class="ghost" id="replaceBtn" type="button">Replace all</button>
            <button class="ghost" id="flagIssueBtn" type="button">Flag issue</button>
          </div>
        </details>
      </div>
      ${warningPanelHtml()}
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
