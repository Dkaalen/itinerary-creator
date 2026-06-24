/** Non-rendering warning/readiness model for debug review UI. */
function warningSeverityLabel(warning) {
  const severity = String(warning?.severity || '').toLowerCase();
  if (severity === 'error' || severity === 'critical') return 'Critical';
  if (severity === 'info') return 'Info';
  return 'Review';
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
  return {level: 'ready', label: 'Export clear', issues};
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

function selectedPageWarnings(pageId) {
  const id = String(pageId || '');
  if (!id) return [];
  return editorReadinessIssues().filter(issue => String(issue.pageId || '') === id);
}
