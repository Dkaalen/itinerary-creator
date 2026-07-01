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
  acknowledgeServerSaveFromPayload(initialPayload);
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
    updateSaveState('recovered', {message: 'Recovered browser draft. Use Save changes to sync it.', recovered: true});
  }
}
function draw() {
  captureEditorScrollState('draw');
  const root = document.getElementById('root');
  const brand = model?.brand || {};
  let h = editorShellOpenHtml(brand) + `
    <div class="editor-toolbar">
      <div class="toolbar-main">
        <div class="toolbar-copy compact"><strong>Editor</strong><span>${picturesAdded() ? 'Pictures added · review pages and save when done.' : 'Edit on the page · Browser recovery saves while you work'}</span><span class="toolbar-legacy-label">${picturesAdded() ? 'Review itinerary with pictures · hover an image to edit it on the canvas' : 'Edit itinerary text · use the formatting inspector for font, size, and color'}</span></div>
      </div>
      <div class="toolbar-stack">
        <div class="toolbar-actions">
          <span id="editCount" class="stat-pill">0 edits pending</span>
          ${pagesMenuHtml()}
          <button class="primary" id="saveBtn" type="button">Save changes</button>
        </div>
        ${saveIssuePanelHtml()}
        ${typeof editorDebugToolbarHtml === 'function' ? editorDebugToolbarHtml() : ''}
      </div>
      ${typeof editorDebugReviewHtml === 'function' ? editorDebugReviewHtml() : ''}
    </div>
    ${editorWorkspaceOpenHtml()}`;
  const coverBg = picturesAdded() ? (model.cover?.cover_image?.data_uri || model.cover?.cover_background_data_uri || '') : '';
  const isBooknordics = brand?.output_brand === 'booknordics_customer';
  const brandColors = brand?.colors || {};
  const daySeparator = isBooknordics ? '-' : '✦';
  const coverInk = picturesAdded() ? (model.cover?.cover_ink || (isBooknordics ? '#00193C' : '#1f3446')) : (isBooknordics ? (brandColors.ink || '#00193C') : '#1f3446');
  const coverMuted = picturesAdded() ? (model.cover?.cover_muted || (isBooknordics ? '#667085' : '#7b746c')) : (isBooknordics ? (brandColors.muted || '#667085') : '#53606c');
  const coverAccent = isBooknordics ? (brandColors.accent || '#FF0041') : (picturesAdded() ? (model.cover?.cover_accent || '#b89555') : '#b89555');
  const coverFocus = model.cover?.cover_image?.crop_focus || 'top';
  const coverStyle = `${coverBg ? `background-image: url('${escAttr(coverBg)}'); background-position: ${focusPos(coverFocus)}; background-size: cover; background-repeat: no-repeat;` : ''} --cover-ink: ${escAttr(coverInk)}; --cover-muted: ${escAttr(coverMuted)}; --cover-accent: ${escAttr(coverAccent)};`;
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
      <div class="day-kicker">DAY ${esc(dayNumber)} <span class="day-kicker-symbol">${daySeparator}</span> ${editableSpan(day.city, `days.${i}.city`, 'day-kicker-city')} <span class="day-kicker-symbol">${daySeparator}</span> ${editableSpan(day.date || '', `days.${i}.date`, 'day-kicker-date', 'Date')}</div>
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
  h += editorWorkspaceCloseHtml();
  root.innerHTML = h;
  attachHandlers();
  restoreEditorScrollState();
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateEditorStats(); syncEditorFrameHeight(); restoreEditorScrollState(); });
}
