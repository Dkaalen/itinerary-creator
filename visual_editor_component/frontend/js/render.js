function coverImageControls(key, label, image) {
  if (!picturesAdded()) return '';
  const img = image || {};
  const imagePageId = key === 'summary_image' ? 'summary' : 'cover';
  const fieldKey = `cover.${key}`;
  const imageBlockAttrs = ` data-editor-page-id="${escAttr(imagePageId)}" data-editor-block-id="${escAttr(imagePageId)}__${escAttr(editorSlug(key))}" data-editor-block-type="image" data-editor-field-key="${escAttr(fieldKey)}" data-editor-field-label="${escAttr(label)}"`;
  return `<div class="cover-image-panel canvas-image-tools" data-cover-image-key="${esc(key)}"${imageBlockAttrs}>
    <strong>${esc(label)}</strong>
    <span class="image-crop-chip">${esc(imageFocusLabel(img.crop_focus))}</span>
    <button type="button" class="ghost" data-select-image-field="${escAttr(fieldKey)}">Image tools</button>
  </div>`;
}

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


function warningSeverityLabel(warning) {
  const severity = String(warning?.severity || '').toLowerCase();
  if (severity === 'error' || severity === 'critical') return 'Critical';
  if (severity === 'info') return 'Info';
  return 'Needs review';
}
function isHiddenAutoFixWarning(warning) {
  const code = String(warning?.code || '').toLowerCase();
  const category = String(warning?.category || '').toLowerCase();
  const severity = String(warning?.severity || '').toLowerCase();
  const text = `${code} ${category} ${String(warning?.message || warning?.excerpt || '').toLowerCase()}`;
  return severity === 'info' && /auto.?fix|autofix|typo|cleanup|normalis|normaliz|correction/.test(text);
}
function allEditorClientWarnings() {
  return Array.isArray(model?.client_output_warnings) ? model.client_output_warnings : [];
}
function groupedClientWarnings() {
  const groups = {critical: [], review: [], info: [], auto_fixes: []};
  allEditorClientWarnings().forEach((warning, index) => {
    const item = Object.assign({warning_index: index}, warning || {});
    const severity = String(item.severity || '').toLowerCase();
    if (isHiddenAutoFixWarning(item)) groups.auto_fixes.push(item);
    else if (severity === 'critical' || severity === 'error') groups.critical.push(item);
    else if (severity === 'info') groups.info.push(item);
    else groups.review.push(item);
  });
  return groups;
}
function warningTargetPageId(warning) {
  if (warning?.page_id) return String(warning.page_id);
  const label = String(warning?.page_label || warning?.day || warning?.excerpt || warning?.message || '');
  const dayMatch = label.match(/\bDay\s+(\d+)\b/i);
  if (dayMatch && Array.isArray(model?.days)) {
    const day = model.days.find((item, index) => {
      const identity = String(item?.day || item?.label || `Day ${index + 1}`);
      return new RegExp(`\\bDay\\s*${dayMatch[1]}\\b`, 'i').test(identity);
    });
    if (day) return pageIdForDay(day, model.days.indexOf(day));
  }
  if (/not included|excluded|exclusion/i.test(label)) return finalPageId('whats_not_included');
  if (/included|inclusion/i.test(label)) return finalPageId('whats_included');
  if (/note/i.test(label)) return finalPageId('important_travel_notes');
  if (/cover/i.test(label)) return 'cover';
  if (/summary|glance|journey/i.test(label)) return 'summary';
  return '';
}
function editorClientWarnings(options = {}) {
  const warnings = allEditorClientWarnings();
  if (options.includeHiddenAutoFixes) return warnings;
  return warnings.filter(warning => !isHiddenAutoFixWarning(warning));
}
function editorImageWarnings() {
  const issues = [];
  (Array.isArray(model?.days) ? model.days : []).forEach((day, dayIndex) => {
    const warnings = Array.isArray(day?.image?.warnings) ? day.image.warnings : [];
    warnings.forEach(warning => issues.push({kind: 'image_warning', dayIndex, pageId: pageIdForDay(day, dayIndex), warning}));
  });
  ['cover_image', 'summary_image'].forEach(key => {
    const warnings = Array.isArray(model?.cover?.[key]?.warnings) ? model.cover[key].warnings : [];
    const pageId = key === 'summary_image' ? 'summary' : 'cover';
    warnings.forEach(warning => issues.push({kind: 'image_warning', pageId, warning}));
  });
  return issues;
}
function pendingImagePreviewIssues() {
  const issues = [];
  (Array.isArray(model?.days) ? model.days : []).forEach((day, dayIndex) => {
    if (day?.image?.pending_preview) issues.push({kind: 'pending_image', pageId: pageIdForDay(day, dayIndex), label: day?.day || `Day ${dayIndex + 1}`});
  });
  ['cover_image', 'summary_image'].forEach(key => {
    if (model?.cover?.[key]?.pending_preview) issues.push({kind: 'pending_image', pageId: key === 'summary_image' ? 'summary' : 'cover', label: key === 'summary_image' ? 'Summary image' : 'Cover image'});
  });
  return issues;
}
function hiddenPageIssues() {
  return (typeof sortedDocumentPages === 'function' ? sortedDocumentPages() : [])
    .filter(page => page?.is_hidden)
    .map(page => ({kind: 'hidden_page', pageId: page.page_id, label: page.title || page.page_id || 'Hidden page', generated: page.page_type !== 'manual'}));
}
function emptyManualPageIssues() {
  return (typeof sortedDocumentPages === 'function' ? sortedDocumentPages() : [])
    .filter(page => page?.page_type === 'manual' && !page?.is_hidden)
    .filter(page => {
      const title = String(page?.title || '').trim();
      const blockText = (page?.manual_blocks || []).map(block => htmlTextContent(block?.editable_fields?.content_html || '')).join(' ').trim();
      return !title && !blockText;
    })
    .map(page => ({kind: 'empty_manual_page', pageId: page.page_id, label: page.title || page.page_id || 'Manual page'}));
}
function editorReadinessIssues() {
  const issues = [];
  if (touchedKeys.size) issues.push({kind: 'unsaved_edits', severity: 'review', label: `${touchedKeys.size} unsaved edit(s)`, pageId: activePageId || ''});
  editorClientWarnings().forEach((warning, index) => issues.push({kind: 'client_warning', severity: warningSeverityLabel(warning), label: warning.excerpt || warning.message || warning.code || 'Review warning', pageId: warningTargetPageId(warning), sourceRowIds: warning.source_row_ids || [], index}));
  editorImageWarnings().forEach(item => issues.push({kind: 'image_warning', severity: 'review', label: item.warning?.message || item.warning?.code || 'Review image quality', pageId: item.pageId}));
  pendingImagePreviewIssues().forEach(item => issues.push({kind: 'pending_image', severity: 'review', label: `${item.label || 'Image'} replacement needs save to refresh preview`, pageId: item.pageId}));
  hiddenPageIssues().forEach(item => issues.push({kind: 'hidden_page', severity: item.generated ? 'review' : 'info', label: `${item.label} is hidden from PDF`, pageId: item.pageId}));
  emptyManualPageIssues().forEach(item => issues.push({kind: 'empty_manual_page', severity: 'info', label: `${item.label} is blank`, pageId: item.pageId}));
  (Array.isArray(model?.issue_flags) ? model.issue_flags : []).forEach((flag, index) => issues.push({kind: 'flagged_issue', severity: 'review', label: flag?.label || flag?.key || `Flagged issue ${index + 1}`, pageId: warningTargetPageId(flag), index}));
  return issues;
}
function pdfReadinessStatus() {
  const issues = editorReadinessIssues();
  const reviewCount = issues.filter(issue => String(issue.severity || '').toLowerCase() !== 'info').length;
  if (reviewCount) return {level: 'review', label: `${reviewCount} item(s) need review`, issues};
  const infoCount = issues.length;
  if (infoCount) return {level: 'info', label: `${infoCount} note(s)`, issues};
  return {level: 'ready', label: 'Ready for client', issues};
}
function readinessIssueText(issue) {
  if (issue.kind === 'unsaved_edits') return 'Save or export to commit the latest editor changes.';
  if (issue.kind === 'client_warning') return 'Check source fidelity and wording before export.';
  if (issue.kind === 'image_warning') return 'Review image quality or replacement choice.';
  if (issue.kind === 'pending_image') return 'Save changes so the PDF preview can refresh the replacement image.';
  if (issue.kind === 'hidden_page') return 'Confirm this page should be excluded from the final itinerary.';
  if (issue.kind === 'empty_manual_page') return 'Add content or delete/restore the page before final export.';
  if (issue.kind === 'flagged_issue') return 'Resolve or clear this manually flagged issue.';
  return 'Review before final PDF export.';
}
function pdfReadinessBadgeHtml() {
  const status = pdfReadinessStatus();
  return `<span id="pdfReadinessBadge" class="stat-pill pdf-readiness ${escAttr(status.level)}">${esc(status.label)}</span>`;
}
function pdfReadinessPanelHtml() {
  const status = pdfReadinessStatus();
  const issues = status.issues.slice(0, 8);
  const rows = issues.length ? issues.map((issue, idx) => {
    const pageId = issue.pageId || '';
    const action = pageId ? `<button type="button" class="ghost mini" data-readiness-page-id="${escAttr(pageId)}">${esc(warningActionLabel(pageId))}</button>` : '';
    return `<li class="readiness-item ${escAttr(issue.kind)}"><strong>${esc(humanizeEditorToken(issue.kind))}</strong><span>${esc(readinessIssueText(issue))}</span><em>${esc(issue.label || 'Review item')}</em>${action}</li>`;
  }).join('') : '<li class="readiness-empty">No visible readiness issues. Still compare preview and PDF after export.</li>';
  const hidden = status.issues.length > issues.length ? `<div class="readiness-more">${status.issues.length - issues.length} more item(s) hidden here.</div>` : '';
  return `<details class="pdf-readiness-panel ${escAttr(status.level)}"><summary>PDF readiness · ${esc(status.label)}</summary><ul>${rows}</ul>${hidden}</details>`;
}
function selectedPageWarnings(pageId) {
  const id = String(pageId || '');
  if (!id) return [];
  return editorReadinessIssues().filter(issue => String(issue.pageId || '') === id);
}
function selectedPageValidationHtml(page) {
  const pageId = page?.page_id || activePageId || '';
  const issues = selectedPageWarnings(pageId);
  if (!pageId) return '<p>Select a page or block to see validation details.</p>';
  if (!issues.length) return '<p>No warnings linked to the selected page.</p>';
  return `<ul class="inspector-warning-list">${issues.slice(0, 6).map(issue => `<li><strong>${esc(humanizeEditorToken(issue.kind))}</strong><span>${esc(readinessIssueText(issue))}</span><em>${esc(issue.label || 'Review item')}</em>${warningSourceChipsHtml(issue.sourceRowIds || [])}</li>`).join('')}</ul>`;
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
function warningActionLabel(pageId) {
  const id = String(pageId || '');
  if (id.startsWith('day-')) return 'Open day page';
  if (id.startsWith('final-')) return 'Open final page';
  if (id === 'cover') return 'Open cover';
  if (id === 'summary') return 'Open summary';
  return 'Open page';
}
function warningSourceChipsHtml(sourceRowIds) {
  const ids = Array.isArray(sourceRowIds) ? sourceRowIds : [];
  if (!ids.length) return '';
  return `<div class="warning-source-row">Source row: ${ids.slice(0, 3).map(id => `<span class="source-chip">${esc(String(id))}</span>`).join('')}</div>`;
}
function warningGroupRowsHtml(warnings) {
  return warnings.slice(0, 8).map((warning) => {
    const location = warningLocationLabel(warning);
    const excerpt = String(warning?.excerpt || warning?.message || warning?.code || 'Review warning');
    const pageId = warningTargetPageId(warning);
    const index = Number.isInteger(warning.warning_index) ? warning.warning_index : 0;
    const action = pageId ? `<button type="button" class="ghost mini" data-warning-page-id="${escAttr(pageId)}" data-warning-index="${index}">${esc(warningActionLabel(pageId))}</button>` : '';
    return `<li><strong>${esc(location)}</strong><span>${esc(warningExplanation(warning))}</span><em>${esc(excerpt)}</em>${warningSourceChipsHtml(warning.source_row_ids || [])}${action}</li>`;
  }).join('');
}
function warningGroupPanelHtml(label, warnings, className, options = {}) {
  if (!warnings.length) return '';
  const rows = warningGroupRowsHtml(warnings);
  const hidden = warnings.length > 8 ? `<div class="warning-panel-more">${warnings.length - 8} more item(s) hidden in this group.</div>` : '';
  const open = options.open ? ' open' : '';
  return `<details class="warning-panel warning-group ${escAttr(className)}"${open}><summary>${esc(label)} · ${warnings.length}</summary><ul>${rows}</ul>${hidden}</details>`;
}
// Compatibility breadcrumb for UI15 static contract: class="warning-panel"><summary>
function warningPanelHtml() {
  const groups = groupedClientWarnings();
  const visibleCount = groups.critical.length + groups.review.length + groups.info.length;
  if (!visibleCount && !groups.auto_fixes.length) return '<p class="review-empty">No client-output warnings in this draft.</p>';
  const panels = [
    warningGroupPanelHtml('Critical', groups.critical, 'critical', {open: true}),
    warningGroupPanelHtml('Needs review', groups.review, 'review', {open: groups.critical.length === 0}),
    warningGroupPanelHtml('Info', groups.info, 'info'),
    warningGroupPanelHtml('Hidden auto-fixes', groups.auto_fixes, 'auto-fixes'),
  ].filter(Boolean).join('');
  return `<div class="warning-panel-stack">${panels}</div>`;
}
function reviewCenterHtml() {
  const groups = groupedClientWarnings();
  const status = pdfReadinessStatus();
  const clientRiskCount = groups.critical.length + groups.review.length;
  const warningText = clientRiskCount ? `${clientRiskCount} client-risk item(s)` : 'No client-risk warnings';
  return `<details class="review-center">
    <summary><strong>Review center</strong><span>${esc(warningText)} · ${esc(status.label)}</span></summary>
    <div class="review-center-grid">${warningPanelHtml()}${pdfReadinessPanelHtml()}</div>
  </details>`;
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
        <div class="toolbar-copy compact"><strong>Editor</strong><span>${picturesAdded() ? 'Pictures added · review pages and save when done.' : 'Edit on the page · Changes autosave quietly while you work'}</span><span class="toolbar-legacy-label">${picturesAdded() ? 'Review itinerary with pictures · select an image, then use the inspector' : 'Edit itinerary text · use the formatting inspector for font, size, and color'}</span></div>
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
