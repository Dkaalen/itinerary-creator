/** Debug-only readiness/review rendering. Normal editor shell does not call this directly. */
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
  return `<details class="pdf-readiness-panel ${escAttr(status.level)}"><summary>Export checks · ${esc(status.label)}</summary><ul>${rows}</ul>${hidden}</details>`;
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

function warningPanelHtml() {
  const groups = groupedClientWarnings();
  const visibleCount = groups.critical.length + groups.review.length + groups.info.length;
  if (!visibleCount && !groups.auto_fixes.length) return '<p class="review-empty">No client-output warnings in this draft.</p>';
  const panels = [
    warningGroupPanelHtml('Critical', groups.critical, 'critical', {open: true}),
    warningGroupPanelHtml('Review', groups.review, 'review', {open: groups.critical.length === 0}),
    warningGroupPanelHtml('Info', groups.info, 'info'),
    warningGroupPanelHtml('Hidden auto-fixes', groups.auto_fixes, 'auto-fixes'),
  ].filter(Boolean).join('');
  return `<div class="warning-panel-stack">${panels}</div>`;
}

function reviewCenterHtml() {
  const groups = groupedClientWarnings();
  const status = pdfReadinessStatus();
  const clientRiskCount = groups.critical.length + groups.review.length;
  const warningText = clientRiskCount ? `${clientRiskCount} export blocker(s)` : 'No export blockers';
  return `<details class="review-center">
    <summary><strong>Document checks</strong><span>${esc(warningText)} · ${esc(status.label)}</span></summary>
    <div class="review-center-grid">${warningPanelHtml()}${pdfReadinessPanelHtml()}</div>
  </details>`;
}
