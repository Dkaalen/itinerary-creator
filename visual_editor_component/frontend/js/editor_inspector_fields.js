// Right-inspector editable field discovery, editing, reset, and compare helpers.
function fieldKindForKey(key) {
  const path = String(key || '');
  if (/\.(?:cover_image|summary_image|image)$/.test(path)) return 'image';
  if (isHtmlEditKey(path)) return 'html';
  return 'text';
}
function inspectorFieldLabelFromKey(key, fallback = '') {
  if (fallback) return fallback;
  const parts = String(key || '').split('.').filter(Boolean);
  const tail = parts[parts.length - 1] || key || 'field';
  if (/^\d+$/.test(tail) && parts.length > 1) return humanizeEditorToken(parts[parts.length - 2]);
  return humanizeEditorToken(tail);
}
function dayIndexForPageId(pageId) {
  const id = String(pageId || '');
  if (!Array.isArray(model?.days)) return -1;
  return model.days.findIndex((day, index) => String(pageIdForDay(day, index)) === id);
}
function addInspectorFieldEntry(entries, key, label = '', kind = '') {
  const path = String(key || '');
  if (!path || entries.some(entry => entry.key === path)) return;
  entries.push({
    key: path,
    label: inspectorFieldLabelFromKey(path, label),
    kind: kind || fieldKindForKey(path),
  });
}
function addInspectorObjectLeafEntries(entries, basePath, value, labelPrefix = '') {
  if (value === null || value === undefined) return;
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      if (item && typeof item === 'object') addInspectorObjectLeafEntries(entries, `${basePath}.${index}`, item, labelPrefix);
      else addInspectorFieldEntry(entries, `${basePath}.${index}`, `${labelPrefix} ${index + 1}`.trim());
    });
    return;
  }
  if (typeof value === 'object') {
    Object.keys(value).forEach(name => {
      const child = value[name];
      const childPath = `${basePath}.${name}`;
      if (child && typeof child === 'object' && !Array.isArray(child)) addInspectorObjectLeafEntries(entries, childPath, child, labelPrefix);
      else addInspectorFieldEntry(entries, childPath, `${labelPrefix} ${humanizeEditorToken(name)}`.trim());
    });
    return;
  }
  addInspectorFieldEntry(entries, basePath, labelPrefix);
}
function inspectorFieldEntriesForSelection(page, block, meta, currentFieldKey = '') {
  const entries = [];
  if (currentFieldKey) addInspectorFieldEntry(entries, currentFieldKey, meta?.field_label || '', fieldKindForKey(currentFieldKey));
  const pageId = String(page?.page_id || meta?.page_id || activePageId || '');
  if (pageId === 'cover') {
    ['cover_kicker','trip_title','trip_subtitle','trip_dates','route_label','destinations_line'].forEach(name => addInspectorFieldEntry(entries, `cover.${name}`));
    addInspectorFieldEntry(entries, 'cover.cover_image', 'Front cover image', 'image');
  } else if (pageId === 'summary') {
    addInspectorFieldEntry(entries, 'summary.trip_glance_title', 'Trip glance title');
    addInspectorObjectLeafEntries(entries, 'summary.trip_glance', model?.summary?.trip_glance || {}, 'Trip glance');
    addInspectorFieldEntry(entries, 'summary.journey_arc_title', 'Journey arc title');
    addInspectorObjectLeafEntries(entries, 'summary.journey_arc_columns', model?.summary?.journey_arc_columns || {}, 'Column');
    addInspectorObjectLeafEntries(entries, 'summary.journey_arc', model?.summary?.journey_arc || [], 'Journey row');
    addInspectorFieldEntry(entries, 'cover.summary_image', 'Page 2 background image', 'image');
  } else if (page?.page_type === 'generated_day' || pageId.startsWith('day-')) {
    const index = dayIndexForPageId(pageId);
    if (index >= 0) {
      ['city','date','title','intro','blocks_html'].forEach(name => addInspectorFieldEntry(entries, `days.${index}.${name}`));
      addInspectorFieldEntry(entries, `days.${index}.image`, 'Day image', 'image');
    }
  } else if (pageId === finalPageId('whats_included')) {
    addInspectorFieldEntry(entries, 'final_pages.whats_included_title', 'Final page title');
    const pages = Array.isArray(model?.final_pages?.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
    if (pages.length) pages.forEach((_, index) => addInspectorFieldEntry(entries, `final_pages.whats_included_pages_html.${index}.html`, `Included page ${index + 1}`, 'html'));
    else addInspectorFieldEntry(entries, 'final_pages.whats_included_html', 'Included content', 'html');
  } else if (pageId === finalPageId('whats_not_included')) {
    addInspectorFieldEntry(entries, 'final_pages.whats_not_included_title', 'Final page title');
    addInspectorFieldEntry(entries, 'final_pages.whats_not_included_html', 'Excluded content', 'html');
  } else if (pageId === finalPageId('important_travel_notes')) {
    addInspectorFieldEntry(entries, 'final_pages.important_travel_notes_title', 'Final page title');
    addInspectorFieldEntry(entries, 'final_pages.important_travel_notes_text', 'Travel notes');
  }
  if (page?.page_type === 'manual') {
    const pageIndex = pageIndexById(page.page_id);
    if (pageIndex >= 0) {
      addInspectorFieldEntry(entries, `document_pages.${pageIndex}.title`, 'Manual page title');
      (Array.isArray(page.manual_blocks) ? page.manual_blocks : []).forEach((manualBlock, blockIndex) => {
        addInspectorFieldEntry(entries, `document_pages.${pageIndex}.manual_blocks.${blockIndex}.editable_fields.content_html`, manualBlock?.title || `Manual text ${blockIndex + 1}`, 'html');
      });
    }
  }
  Object.keys(block?.editable_fields || {}).forEach(field => {
    const fieldKey = currentFieldKey && currentFieldKey.endsWith(`.${field}`) ? currentFieldKey : '';
    if (fieldKey) addInspectorFieldEntry(entries, fieldKey, humanizeEditorToken(field));
  });
  return entries;
}
function inspectorFieldValue(key) {
  const el = findEditableByKey(key);
  if (el) return editableValue(el);
  const value = getByPath(model, key);
  if (value && typeof value === 'object' && 'html' in value) return String(value.html || '');
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}
function syncDocumentPageTitleForField(key, value) {
  const path = String(key || '');
  let page = null;
  let match = path.match(/^days\.(\d+)\.title$/);
  if (match) page = contractPage(safeDayPageId(Number(match[1])));
  if (path === 'final_pages.whats_included_title') page = contractPage(finalPageId('whats_included'));
  if (path === 'final_pages.whats_not_included_title') page = contractPage(finalPageId('whats_not_included'));
  if (path === 'final_pages.important_travel_notes_title') page = contractPage(finalPageId('important_travel_notes'));
  match = path.match(/^document_pages\.(\d+)\.title$/);
  if (match) page = documentPages()[Number(match[1])] || page;
  if (page) page.title = String(value || '');
}
function applyInspectorFieldEdit(key, value, options = {}) {
  const path = String(key || '');
  if (!path || fieldKindForKey(path) === 'image') return;
  const el = findEditableByKey(path);
  if (el) {
    if (isHtmlEditKey(path)) el.innerHTML = value || '';
    else el.innerText = value || '';
  }
  setByPath(model, path, el ? editableValue(el) : value);
  syncDocumentPageTitleForField(path, el ? editableValue(el) : value);
  const meta = inferEditorBlockMetaForKey(path, '');
  activeFieldKey = path;
  activePageId = meta.page_id || activePageId;
  activeBlockId = meta.block_id || activeBlockId;
  markTouched(path);
  requestAnimationFrame(() => {
    highlightWarnings();
    adjustDayImages();
    updateSelectionUi();
    updateEditorStats();
    if (options.refreshInspector) updateRightInspector();
  });
}
function resetFieldByKey(key) {
  const path = String(key || activeFieldKey || '');
  if (!path || fieldKindForKey(path) === 'image') {
    notifyEditor('Select a text field to reset. Images use the image tools.');
    return;
  }
  const el = findEditableByKey(path);
  if (el) pushUndo(el, editableValue(el));
  const restored = restoreValueForKey(path);
  const resetValue = restored === undefined || restored === null ? '' : String(restored);
  applyInspectorFieldEdit(path, resetValue, {refreshInspector: true});
  notifyEditor(generatedValueForKey(path) !== undefined ? 'Field restored to generated value' : 'Field restored to original loaded value');
}
function selectInspectorField(key) {
  const path = String(key || '');
  if (!path) return;
  const meta = inferEditorBlockMetaForKey(path, '');
  activeFieldKey = path;
  activePageId = meta.page_id || activePageId;
  activeBlockId = meta.block_id || activeBlockId;
  const el = findEditableByKey(path);
  if (el) {
    el.focus({preventScroll: true});
  }
  updateSelectionUi();
  updateRightInspector();
}
function renderInspectorFieldList(entries, currentFieldKey) {
  if (!entries.length) return '<li>No direct editable fields exposed yet</li>';
  return entries.slice(0, 24).map(entry => {
    const value = entry.kind === 'image' ? 'Image selected on canvas' : inspectorFieldValue(entry.key);
    const selected = entry.key === currentFieldKey ? ' active' : '';
    const reset = entry.kind === 'image' ? '' : `<button type="button" class="ghost mini" data-inspector-reset-field-key="${escAttr(entry.key)}">Reset</button>`;
    return `<li class="inspector-field-row${selected}"><button type="button" class="field-select" data-inspector-field-key="${escAttr(entry.key)}"><strong>${esc(entry.label)}</strong><span>${esc(entry.kind === 'html' ? htmlTextContent(value).slice(0, 72) : String(value).slice(0, 72)) || 'Empty'}</span></button>${reset}</li>`;
  }).join('');
}
function renderInspectorFieldEditor(fieldKey) {
  const key = String(fieldKey || '');
  if (!key) {
    return `<div class="inspector-card field-editor-card empty"><div class="inspector-kicker">Field editor</div><p>Select a field from the canvas or the field list to edit it here.</p></div>`;
  }
  if (fieldKindForKey(key) === 'image') {
    return `<div class="inspector-card field-editor-card"><div class="inspector-kicker">Field editor</div><strong>${esc(inspectorFieldLabelFromKey(key))}</strong><p>This is an image field. Edit it directly on the image canvas so preview and PDF stay in sync.</p></div>`;
  }
  const value = inspectorFieldValue(key);
  const rows = fieldKindForKey(key) === 'html' || value.length > 120 ? 6 : 3;
  return `<div class="inspector-card field-editor-card"><div class="inspector-kicker">Field editor</div><label for="inspectorFieldEditor">${esc(inspectorFieldLabelFromKey(key))}</label><textarea id="inspectorFieldEditor" rows="${rows}" data-inspector-edit-key="${escAttr(key)}">${esc(value)}</textarea><div class="inspector-button-grid two"><button type="button" class="ghost" id="inspectorApplyFieldBtn">Apply field edit</button><button type="button" class="ghost" id="inspectorResetSingleFieldBtn">Reset field</button></div><p>Edit the selected field here or directly on the page. Rich content fields preserve controlled HTML/classes for PDF parity.</p></div>`;
}
function resetSelectedInspectorField() {
  resetFieldByKey(activeFieldKey || selectedInspectorMeta().fieldKey);
}
function resetSelectionFieldsToGenerated() {
  const {fieldKey, meta, page, block} = selectedInspectorMeta();
  const entries = inspectorFieldEntriesForSelection(page, block, meta, fieldKey).filter(entry => entry.kind !== 'image');
  let count = 0;
  entries.forEach(entry => {
    const generated = generatedValueForKey(entry.key);
    if (generated === undefined || generated === null) return;
    applyInspectorFieldEdit(entry.key, String(generated), {refreshInspector: false});
    count += 1;
  });
  if (count) {
    notifyEditor(`${count} field(s) restored to generated values`);
    draw();
  } else {
    notifyEditor('No generated values are available for this selection');
  }
}
function renderInspectorCompareTools(fieldKey, fieldEntries = []) {
  const key = String(fieldKey || '');
  const entries = Array.isArray(fieldEntries) ? fieldEntries : [];
  const changedEntries = entries.filter(entry => entry.kind !== 'image' && fieldDiffState(entry.key).changed);
  if (!key || fieldKindForKey(key) === 'image') {
    const summary = changedEntries.length ? `${changedEntries.length} edited field(s) differ from generated content.` : 'Select a text field to compare against generated content.';
    return `<div class="inspector-card compare-card"><div class="inspector-kicker">Compare & restore</div><p>${esc(summary)}</p><button type="button" class="ghost full-width" id="inspectorRestoreSelectionGeneratedBtn" ${changedEntries.length ? '' : 'disabled'}>Restore changed fields on selection</button></div>`;
  }
  const diff = fieldDiffState(key);
  const generatedLabel = diff.hasGenerated ? (diff.changed ? 'Edited' : 'Matches generated') : 'No generated snapshot';
  const currentText = compareTextForValue(diff.current, fieldKindForKey(key)).slice(0, 420);
  const generatedText = compareTextForValue(diff.generated, fieldKindForKey(key)).slice(0, 420);
  const generatedBlock = diff.hasGenerated
    ? `<div class="compare-column"><strong>Generated</strong><p>${esc(generatedText || 'Empty')}</p></div>`
    : `<p class="compare-empty">Generated source is not available for this field, usually because it is a manual page or new custom block.</p>`;
  return `<div class="inspector-card compare-card ${diff.changed ? 'changed' : 'clean'}"><div class="inspector-kicker">Compare & restore</div><strong>${esc(generatedLabel)}</strong><div class="compare-grid"><div class="compare-column"><strong>Current</strong><p>${esc(currentText || 'Empty')}</p></div>${generatedBlock}</div><div class="inspector-button-grid two"><button type="button" class="ghost" id="inspectorRestoreCurrentGeneratedBtn" ${diff.hasGenerated ? '' : 'disabled'}>Restore this field</button><button type="button" class="ghost" id="inspectorRestoreSelectionGeneratedBtn" ${changedEntries.length ? '' : 'disabled'}>Restore changed fields</button></div></div>`;
}
