function selectedInspectorMeta() {
  const el = selectedEditorElement();
  const fieldKey = activeFieldKey || el?.getAttribute?.('data-editor-field-key') || el?.getAttribute?.('data-edit-key') || '';
  const meta = inferEditorBlockMetaForKey(fieldKey, el?.getAttribute?.('data-editor-field-label') || '');
  const page = contractPage(activePageId || meta.page_id) || {};
  const block = contractBlock(page, activeBlockId || meta.block_id) || {};
  return {el, fieldKey, meta, page, block};
}
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
    const value = entry.kind === 'image' ? 'Image tools' : inspectorFieldValue(entry.key);
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
    return `<div class="inspector-card field-editor-card"><div class="inspector-kicker">Field editor</div><strong>${esc(inspectorFieldLabelFromKey(key))}</strong><p>This is an image field. Use the image tools below so preview and PDF stay in sync.</p></div>`;
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
function sourceRowLookup() {
  return model?.source_rows || initialPayload?.source_rows || {};
}
function renderSourceRowDetails(sourceRowIds) {
  const ids = Array.isArray(sourceRowIds) ? sourceRowIds : [];
  const lookup = sourceRowLookup();
  if (!ids.length) return '<span class="empty-source">No source rows linked</span>';
  return ids.slice(0, 8).map(id => {
    const row = lookup[String(id)] || {};
    const title = row.title || row.source_text || id;
    const meta = [row.day, row.city, row.type].filter(Boolean).join(' · ');
    const details = row.source_text || [row.title, row.details].filter(Boolean).join(' | ') || 'No source text available in payload.';
    return `<details class="source-row-detail"><summary><span class="source-chip">${esc(id)}</span><strong>${esc(String(title).slice(0, 90))}</strong></summary><div class="source-row-meta">${esc(meta || 'Source row')}</div><p>${esc(String(details).slice(0, 700))}</p></details>`;
  }).join('');
}
function renderSourceRows(sourceRowIds) {
  return renderSourceRowDetails(sourceRowIds);
}
function renderInspectorSelectionCard(fieldKey, page, block, meta) {
  const key = String(fieldKey || '');
  if (!key && !activePageId) return '';
  const isImage = fieldKindForKey(key) === 'image';
  const title = key ? inspectorFieldLabelFromKey(key, meta?.field_label || '') : (page?.title || 'Page');
  const pageLabel = page?.title || meta?.page_title || activePageId || 'Current page';
  const blockLabel = block?.title || humanizeEditorToken(block?.block_type || meta?.block_type || (isImage ? 'Image' : 'Text'));
  return `<div class="inspector-card selection-card ${isImage ? 'image' : 'text'}"><div class="inspector-kicker">Selection</div><strong>${esc(title)}</strong><dl><dt>Page</dt><dd>${esc(pageLabel)}</dd><dt>Type</dt><dd>${esc(blockLabel)}</dd></dl></div>`;
}

function renderInspectorTextTools(hasBlock) {
  const canStyle = !!canUsePdfSafeTextTools();
  const disabled = canStyle ? '' : 'disabled';
  const hint = canStyle
    ? 'Formatting applies to the selected canvas text and to what you type next in that selection.'
    : 'Select text on the canvas to enable formatting.';
  return `<div class="inspector-card text-tools-card"><div class="inspector-kicker">Formatting</div>
    <label class="inspector-control-label" for="inspectorFontFamilyPreset">Font</label>
    <select id="inspectorFontFamilyPreset" ${disabled} aria-label="Font family">${controlledPresetOptionsHtml('font_families', 'Choose font')}</select>
    <label class="inspector-control-label" for="inspectorFontSizePreset">Size</label>
    <select id="inspectorFontSizePreset" ${disabled} aria-label="Font size">${controlledPresetOptionsHtml('font_sizes', 'Choose size')}</select>
    <label class="inspector-control-label" for="inspectorTextStylePreset">Paragraph style</label>
    <select id="inspectorTextStylePreset" ${disabled} aria-label="Paragraph style">${controlledPresetOptionsHtml('text_styles', 'Choose style')}</select>
    <label class="inspector-control-label" for="inspectorColorPreset">Text color / highlight</label>
    <select id="inspectorColorPreset" ${disabled} aria-label="Text color and highlight">${controlledPresetOptionsHtml('colors', 'Choose color')}</select>
    <div class="inspector-button-grid">
      <button type="button" class="ghost" id="inspectorCompactSpacingBtn" ${disabled}>Compact</button>
      <button type="button" class="ghost" id="inspectorNormalSpacingBtn" ${disabled}>Normal spacing</button>
      <button type="button" class="ghost" id="inspectorClearFormattingBtn" ${disabled}>Clear formatting</button>
    </div>
    <p>${esc(hint)}</p>
  </div>`;
}


function selectedImageContextFromField(fieldKey) {
  const key = String(fieldKey || '');
  let match = key.match(/^days\.(\d+)\.image$/);
  if (match) {
    const dayIndex = Number(match[1]);
    const day = Array.isArray(model.days) ? model.days[dayIndex] : null;
    if (!day) return null;
    if (!day.image) day.image = {mode: 'auto', path: '', crop_focus: 'top', options: []};
    return {
      kind: 'day',
      label: day.day || `Day ${dayIndex + 1}`,
      fieldKey: key,
      dayIndex,
      coverKey: '',
      image: day.image,
      supportsUpload: true,
    };
  }
  match = key.match(/^cover\.(cover_image|summary_image)$/);
  if (match) {
    const coverKey = match[1];
    if (!model.cover) model.cover = {};
    if (!model.cover[coverKey]) model.cover[coverKey] = {mode: 'auto', path: '', crop_focus: 'top', options: []};
    return {
      kind: 'cover',
      label: coverKey === 'summary_image' ? 'Page 2 background image' : 'Front cover image',
      fieldKey: key,
      dayIndex: null,
      coverKey,
      image: model.cover[coverKey],
      supportsUpload: false,
    };
  }
  return null;
}
function selectedImageContext() {
  const {fieldKey} = selectedInspectorMeta();
  return selectedImageContextFromField(fieldKey);
}
function imageOptionReason(image) {
  const path = String(image?.path || '');
  if (!path) return image?.reason || image?.auto_reason || '';
  const option = (Array.isArray(image?.options) ? image.options : []).find(opt => String(opt?.path || '') === path);
  return option?.reason || image?.reason || image?.auto_reason || '';
}
function imageOptionsHtml(image) {
  const options = Array.isArray(image?.options) ? image.options : [];
  return options.map((opt, idx) => `<option value="${escAttr(opt.path || '')}" data-option-index="${idx}" title="${escAttr(opt.reason || '')}" ${opt.path === image?.path ? 'selected' : ''}>${esc(opt.name || opt.path || `Option ${idx + 1}`)}</option>`).join('');
}
function imageWarningsHtml(image) {
  const warnings = Array.isArray(image?.warnings) ? image.warnings : [];
  if (!warnings.length) return '<span class="empty-source">No image warnings</span>';
  return `<ul class="inspector-warning-list">${warnings.slice(0, 4).map(warning => `<li>${esc(warning?.message || warning?.code || 'Review image')}</li>`).join('')}</ul>`;
}
function imageModeLabel(image) {
  const mode = String(image?.mode || 'auto');
  if (mode === 'manual') return 'Manual replacement';
  if (mode === 'none') return 'Removed';
  return 'Automatic';
}
function setImageAutomatic(ctx) {
  if (!ctx?.image) return;
  ctx.image.mode = 'auto';
  ctx.image.path = '';
  ctx.image.data_uri = ctx.image.auto_data_uri || ctx.image.data_uri || '';
  ctx.image.name = ctx.image.auto_name || ctx.image.name || '';
  ctx.image.pending_preview = false;
  markTouched(ctx.fieldKey);
}
function setImageRemoved(ctx) {
  if (!ctx?.image) return;
  ctx.image.mode = 'none';
  ctx.image.path = '';
  ctx.image.data_uri = '';
  ctx.image.name = '';
  ctx.image.pending_preview = false;
  markTouched(ctx.fieldKey);
}
function setImageManualPath(ctx, path) {
  if (!ctx?.image || !path) return false;
  const selected = (Array.isArray(ctx.image.options) ? ctx.image.options : []).find(opt => opt.path === path) || {};
  ctx.image.mode = 'manual';
  ctx.image.path = path;
  ctx.image.data_uri = '';
  ctx.image.name = selected.name || path.split('/').pop() || '';
  ctx.image.pending_preview = true;
  markTouched(ctx.fieldKey);
  return true;
}
function setImageCropFocus(ctx, focus) {
  if (!ctx?.image) return;
  ctx.image.crop_focus = focus || 'top';
  markTouched(ctx.fieldKey);
}
function updateImagePreviewForContext(ctx) {
  if (!ctx?.fieldKey) return;
  if (ctx.kind === 'day') {
    const img = document.querySelector(`[data-editor-field-key="${CSS.escape(ctx.fieldKey)}"] img`);
    if (img) img.style.objectPosition = focusPos(ctx.image?.crop_focus || 'top');
    const chip = document.querySelector(`[data-editor-field-key="${CSS.escape(ctx.fieldKey)}"] .image-crop-chip`);
    if (chip) chip.textContent = imageFocusLabel(ctx.image?.crop_focus || 'top');
  }
  if (ctx.kind === 'cover') {
    const page = document.querySelector(`[data-page-id="${CSS.escape(ctx.coverKey === 'summary_image' ? 'summary' : 'cover')}"] .a4-page`);
    if (page) page.style.backgroundPosition = focusPos(ctx.image?.crop_focus || 'top');
    const chip = document.querySelector(`[data-editor-field-key="${CSS.escape(ctx.fieldKey)}"] .image-crop-chip`);
    if (chip) chip.textContent = imageFocusLabel(ctx.image?.crop_focus || 'top');
  }
}
function applyImageContextAction(ctx, action, value = '') {
  if (!ctx) {
    notifyEditor('Select an image first.');
    return;
  }
  collect();
  if (action === 'auto') setImageAutomatic(ctx);
  if (action === 'none') setImageRemoved(ctx);
  if (action === 'manual') {
    if (!setImageManualPath(ctx, value)) {
      notifyEditor('Choose an image replacement first.');
      return;
    }
  }
  if (action === 'focus') setImageCropFocus(ctx, value);
  activeFieldKey = ctx.fieldKey || activeFieldKey;
  notifyEditor(action === 'focus' ? 'Image crop updated' : 'Image selection updated');
  if (action === 'focus') {
    updateImagePreviewForContext(ctx);
    updateRightInspector();
    updateEditorStats();
    return;
  }
  draw();
}
function renderInspectorImageTools(fieldKey) {
  const ctx = selectedImageContextFromField(fieldKey);
  if (!ctx || !picturesAdded()) return '';
  const image = ctx.image || {};
  const focus = image.crop_focus || 'top';
  const reason = imageOptionReason(image);
  const options = imageOptionsHtml(image);
  const hasOptions = !!options;
  const upload = ctx.supportsUpload
    ? `<label class="upload-label inspector-upload-label">Upload<input type="file" accept="image/png,image/jpeg,image/webp" id="inspectorImageUploadInput"></label>`
    : '<p class="inspector-mini-note">Upload is currently available on day images. Cover/page-2 images can use the curated replacement list.</p>';
  const pending = image.pending_preview ? '<p class="inspector-mini-note pending-preview-note">Replacement selected. Save changes to refresh the preview image.</p>' : '';
  return `<div class="inspector-card image-tools-card"><div class="inspector-kicker">Image tools</div>
    <strong>${esc(ctx.label)}</strong>
    <dl><dt>Mode</dt><dd>${esc(imageModeLabel(image))}</dd><dt>Crop</dt><dd>${esc(imageFocusLabel(focus))}</dd><dt>Name</dt><dd>${esc(image.name || image.auto_name || '—')}</dd></dl>
    ${pending}
    <label class="inspector-control-label" for="inspectorImageFocus">Crop position</label>
    <select id="inspectorImageFocus" aria-label="Image crop position">
      <option value="top" ${focus === 'top' ? 'selected' : ''}>Sky / upper crop</option>
      <option value="center" ${focus === 'center' ? 'selected' : ''}>Center crop</option>
      <option value="bottom" ${focus === 'bottom' ? 'selected' : ''}>Lower crop</option>
    </select>
    <label class="inspector-control-label" for="inspectorImageBank">Replacement image</label>
    <select id="inspectorImageBank" ${hasOptions ? '' : 'disabled'} aria-label="Replacement image"><option value="">Choose replacement…</option>${options}</select>
    <div class="inspector-button-grid">
      <button type="button" class="ghost" id="inspectorImageAutomaticBtn">Automatic</button>
      <button type="button" class="ghost" id="inspectorImageManualBtn" ${hasOptions ? '' : 'disabled'}>Use selected</button>
      <button type="button" class="danger" id="inspectorImageRemoveBtn">Remove image</button>
    </div>
    ${upload}
    <div class="inspector-image-meta"><div class="inspector-kicker">Why this image</div><p>${esc(reason || 'No selection reason available yet.')}</p></div>
    <div class="inspector-image-meta"><div class="inspector-kicker">Quality warnings</div>${imageWarningsHtml(image)}</div>
  </div>`;
}

function renderInspectorLayoutTools(hasBlock, page, block) {
  const hasPage = !!(page && page.page_id);
  if (!hasPage && !hasBlock) return '';
  const pageOverrides = page?.page_overrides || {};
  const blockOverrides = block?.style_overrides || {};
  const isManualPage = page?.page_type === 'manual';
  const selectedManualBlock = !!manualBlockContextFromSelection();
  const pageHidden = !!page?.is_hidden;
  const spacing = String(pageOverrides.spacing_density || 'standard');
  const blockSpacing = String(blockOverrides.spacing_density || 'inherit');
  const pageDisabled = hasPage ? '' : 'disabled';
  const manualDisabled = isManualPage ? '' : 'disabled';
  const blockDisabled = hasBlock ? '' : 'disabled';
  const manualBlockDisabled = selectedManualBlock ? '' : 'disabled';
  const blockTools = hasBlock ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorBlockSpacing">Selected block spacing</label>
    <select id="inspectorBlockSpacing" ${blockDisabled} aria-label="Selected block spacing">
      <option value="inherit" ${blockSpacing === 'inherit' ? 'selected' : ''}>Inherit page spacing</option>
      <option value="compact" ${blockSpacing === 'compact' ? 'selected' : ''}>Compact</option>
      <option value="standard" ${blockSpacing === 'standard' ? 'selected' : ''}>Standard</option>
      <option value="comfortable" ${blockSpacing === 'comfortable' ? 'selected' : ''}>Comfortable</option>
    </select>
    <label class="inspector-checkbox"><input type="checkbox" id="inspectorKeepBlockTogether" ${blockOverrides.keep_block_together ? 'checked' : ''} ${blockDisabled}> Keep selected block together</label>
  </div>` : '';
  const manualBlockTools = selectedManualBlock ? `<div class="inspector-layout-section">
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorMoveBlockUpBtn" ${manualBlockDisabled}>Move block up</button>
      <button type="button" class="ghost" id="inspectorMoveBlockDownBtn" ${manualBlockDisabled}>Move block down</button>
      <button type="button" class="ghost" id="inspectorDuplicateBlockBtn" ${manualBlockDisabled}>Duplicate block</button>
      <button type="button" class="danger" id="inspectorDeleteBlockBtn" ${manualBlockDisabled}>Delete block</button>
    </div>
  </div>` : '';
  const manualPageTools = isManualPage ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorManualBlockTemplate">Insert block on manual page</label>
    <select id="inspectorManualBlockTemplate" ${manualDisabled} aria-label="Manual block template">${manualBlockTemplateOptionsHtml('text')}</select>
    <button type="button" class="ghost full-width" id="inspectorInsertManualBlockBtn" ${manualDisabled}>Insert selected block</button>
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorDuplicatePageBtn" ${manualDisabled}>Duplicate page</button>
      <button type="button" class="ghost" id="inspectorAddManualBlockBtn" ${manualDisabled}>Add text block</button>
    </div>
  </div>` : '';
  const pageTools = hasPage ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorPageSpacing">Page spacing</label>
    <select id="inspectorPageSpacing" ${pageDisabled} aria-label="Page spacing">
      <option value="standard" ${spacing === 'standard' ? 'selected' : ''}>Standard</option>
      <option value="compact" ${spacing === 'compact' ? 'selected' : ''}>Compact</option>
      <option value="comfortable" ${spacing === 'comfortable' ? 'selected' : ''}>Comfortable</option>
    </select>
    <label class="inspector-checkbox"><input type="checkbox" id="inspectorKeepPageTogether" ${pageOverrides.keep_page_together ? 'checked' : ''} ${pageDisabled}> Keep page together</label>
    <div class="inspector-button-grid">
      <button type="button" class="ghost" id="inspectorHidePageBtn" ${hasPage && !pageHidden ? '' : 'disabled'}>Delete page</button>
      <button type="button" class="ghost" id="inspectorRestorePageBtn" ${hasPage && pageHidden ? '' : 'disabled'}>Restore page</button>
      <button type="button" class="ghost" id="inspectorResetPageLayoutBtn" ${pageDisabled}>Reset layout</button>
    </div>
  </div>` : '';
  const manualTemplateTools = hasPage ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorManualPageTemplate">Manual page template</label>
    <select id="inspectorManualPageTemplate" aria-label="Manual page template">${manualPageTemplateOptionsHtml('blank')}</select>
    <button type="button" class="ghost full-width" id="inspectorAddTemplatePageBtn">Add template page</button>
  </div>` : '';
  return `<details class="inspector-card layout-tools-card"><summary><span>More page options</span><em>Layout tools</em></summary>
    ${pageTools}
    ${manualPageTools}
    ${blockTools}
    ${manualBlockTools}
    ${manualTemplateTools}
    <p class="inspector-mini-note">Page move and delete shortcuts are also available above each itinerary page.</p>
  </details>`;
}

function renderRightInspector() {
  const {fieldKey, meta, page, block} = selectedInspectorMeta();
  const hasBlock = !!(fieldKey || activeBlockId);
  const hasImage = fieldKindForKey(fieldKey) === 'image';
  const emptyState = hasBlock
    ? ''
    : `<div class="inspector-card empty inspector-empty-state"><strong>Select text on the itinerary</strong><p>Use the canvas for text editing. Use these controls only for font, size, color, spacing, and selected-item properties.</p></div>`;
  const imageTools = hasImage ? renderInspectorImageTools(fieldKey) : '';
  const selectionCard = hasBlock ? renderInspectorSelectionCard(fieldKey, page, block, meta) : '';
  return `<aside class="right-inspector" aria-label="Formatting and selected-item properties">
    <div class="inspector-title"><strong>Formatting</strong><span>${hasImage ? 'Image' : (canUsePdfSafeTextTools() ? 'Text' : 'Ready')}</span></div>
    ${emptyState}
    ${selectionCard}
    ${renderInspectorTextTools(hasBlock)}
    ${imageTools}
  </aside>`;
}

function updateRightInspector() {
  const inspector = document.querySelector('.right-inspector');
  if (!inspector) return;
  inspector.outerHTML = renderRightInspector();
  attachInspectorHandlers();
  requestAnimationFrame(() => syncEditorFrameHeight());
}
function attachInspectorHandlers() {
  document.querySelectorAll('.text-tools-card select, .text-tools-card button').forEach(control => {
    control.addEventListener('mousedown', rememberCanvasSelection, {capture: true});
    control.addEventListener('focus', rememberCanvasSelection, {capture: true});
  });
  document.getElementById('inspectorFontFamilyPreset')?.addEventListener('change', event => {
    if (event.target.value) applyFontFamilyPreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorFontSizePreset')?.addEventListener('change', event => {
    if (event.target.value) applyFontSizePreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorTextStylePreset')?.addEventListener('change', event => {
    if (event.target.value) applyTextStylePreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorColorPreset')?.addEventListener('change', event => {
    if (event.target.value) applyColorPreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorCompactSpacingBtn')?.addEventListener('click', () => { applySpacingPreset('compact'); updateRightInspector(); });
  document.getElementById('inspectorNormalSpacingBtn')?.addEventListener('click', () => { applySpacingPreset('normal'); updateRightInspector(); });
  document.getElementById('inspectorClearFormattingBtn')?.addEventListener('click', clearSelectedFormatting);
  document.getElementById('inspectorImageFocus')?.addEventListener('change', event => {
    applyImageContextAction(selectedImageContext(), 'focus', event.target.value);
  });
  document.getElementById('inspectorImageAutomaticBtn')?.addEventListener('click', () => {
    applyImageContextAction(selectedImageContext(), 'auto');
  });
  document.getElementById('inspectorImageRemoveBtn')?.addEventListener('click', () => {
    applyImageContextAction(selectedImageContext(), 'none');
  });
  document.getElementById('inspectorImageManualBtn')?.addEventListener('click', () => {
    const value = document.getElementById('inspectorImageBank')?.value || '';
    applyImageContextAction(selectedImageContext(), 'manual', value);
  });
  document.getElementById('inspectorImageUploadInput')?.addEventListener('change', event => {
    const ctx = selectedImageContext();
    const file = event.target.files && event.target.files[0];
    if (!ctx || ctx.kind !== 'day' || !file) return;
    const reader = new FileReader();
    reader.onload = () => {
      uploadedImages[ctx.dayIndex] = {filename: file.name, data_uri: reader.result, season: 'Summer', label: file.name.replace(/\.[^.]+$/, '')};
      ctx.image.mode = 'manual';
      ctx.image.path = '';
      ctx.image.data_uri = reader.result;
      ctx.image.name = file.name.replace(/\.[^.]+$/, '');
      ctx.image.pending_preview = false;
      markTouched(ctx.fieldKey);
      notifyEditor('Uploaded image selected');
      draw();
    };
    reader.readAsDataURL(file);
  });
  document.getElementById('inspectorPageSpacing')?.addEventListener('change', event => {
    setSelectedPageOverride('spacing_density', event.target.value === 'standard' ? '' : event.target.value);
  });
  document.getElementById('inspectorKeepPageTogether')?.addEventListener('change', event => {
    setSelectedPageOverride('keep_page_together', !!event.target.checked);
  });
  document.getElementById('inspectorBlockSpacing')?.addEventListener('change', event => {
    setSelectedBlockOverride('spacing_density', event.target.value === 'inherit' ? '' : event.target.value);
  });
  document.getElementById('inspectorKeepBlockTogether')?.addEventListener('change', event => {
    setSelectedBlockOverride('keep_block_together', !!event.target.checked);
  });
  document.getElementById('inspectorHidePageBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) hideDocumentPage(page.page_id); });
  document.getElementById('inspectorRestorePageBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) restoreDocumentPage(page.page_id); });
  document.getElementById('inspectorResetPageLayoutBtn')?.addEventListener('click', resetSelectedPageLayout);
  document.getElementById('inspectorMovePageUpBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) moveDocumentPage(page.page_id, -1); });
  document.getElementById('inspectorMovePageDownBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) moveDocumentPage(page.page_id, 1); });
  document.getElementById('inspectorDuplicatePageBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) duplicateManualPage(page.page_id); });
  document.getElementById('inspectorAddManualBlockBtn')?.addEventListener('click', addManualTextBlockToSelectedPage);
  document.getElementById('inspectorAddTemplatePageBtn')?.addEventListener('click', () => {
    addManualPage(document.getElementById('inspectorManualPageTemplate')?.value || 'blank');
  });
  document.getElementById('inspectorInsertManualBlockBtn')?.addEventListener('click', () => {
    addManualBlockToSelectedPage(document.getElementById('inspectorManualBlockTemplate')?.value || 'text');
  });
  document.getElementById('inspectorMoveBlockUpBtn')?.addEventListener('click', () => moveSelectedManualBlock(-1));
  document.getElementById('inspectorMoveBlockDownBtn')?.addEventListener('click', () => moveSelectedManualBlock(1));
  document.getElementById('inspectorDuplicateBlockBtn')?.addEventListener('click', duplicateSelectedManualBlock);
  document.getElementById('inspectorDeleteBlockBtn')?.addEventListener('click', deleteSelectedManualBlock);
  document.querySelectorAll('[data-inspector-field-key]').forEach(btn => {
    btn.addEventListener('click', () => selectInspectorField(btn.getAttribute('data-inspector-field-key')));
  });
  document.querySelectorAll('[data-inspector-reset-field-key]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.stopPropagation();
      resetFieldByKey(btn.getAttribute('data-inspector-reset-field-key'));
    });
  });
  document.getElementById('inspectorFieldEditor')?.addEventListener('input', event => {
    applyInspectorFieldEdit(event.target.getAttribute('data-inspector-edit-key'), event.target.value);
  });
  document.getElementById('inspectorFieldEditor')?.addEventListener('blur', event => {
    applyInspectorFieldEdit(event.target.getAttribute('data-inspector-edit-key'), event.target.value, {refreshInspector: false});
  });
  document.getElementById('inspectorApplyFieldBtn')?.addEventListener('click', () => {
    const editor = document.getElementById('inspectorFieldEditor');
    if (editor) {
      applyInspectorFieldEdit(editor.getAttribute('data-inspector-edit-key'), editor.value, {refreshInspector: false});
      draw();
    }
  });
  document.getElementById('inspectorRestoreCurrentGeneratedBtn')?.addEventListener('click', resetSelectedInspectorField);
  document.getElementById('inspectorRestoreSelectionGeneratedBtn')?.addEventListener('click', resetSelectionFieldsToGenerated);
  document.getElementById('inspectorResetSingleFieldBtn')?.addEventListener('click', resetSelectedInspectorField);
  document.getElementById('inspectorResetFieldBtn')?.addEventListener('click', resetSelectedInspectorField);
  document.getElementById('inspectorFlagIssueBtn')?.addEventListener('click', flagSelectedIssue);
  document.getElementById('inspectorClearSelectionBtn')?.addEventListener('click', () => {
    activeBlockId = null;
    activeFieldKey = null;
    updateSelectionUi();
    updateRightInspector();
  });
}
