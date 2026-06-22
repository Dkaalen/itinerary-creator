function markTouched(key) {
  if (key) touchedKeys.add(key);
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = 'Unsaved edits';
    note.classList.add('show');
  }
  persistLocalDraft();
  scheduleServerAutosave();
  updateEditorStats();
}
function isHtmlEditKey(key) {
  return key && (key.endsWith('.blocks_html') || key.endsWith('.content_html') || key.endsWith('.whats_included_html') || key.endsWith('.whats_not_included_html') || key.includes('.editable_fields.content_html') || key.includes('.whats_included_pages_html.'));
}
function editableValue(el) {
  if (!el) return '';
  const key = el.getAttribute('data-edit-key') || '';
  if (isHtmlEditKey(key)) return el.innerHTML.trim();
  return el.innerText.replace(/\u00a0/g, ' ').replace(/\s*\n+\s*/g, key === 'cover.destinations_line' ? ' · ' : ' ').trim();
}
function writeEditableValue(el, value) {
  if (!el) return;
  const key = el.getAttribute('data-edit-key') || '';
  if (isHtmlEditKey(key)) el.innerHTML = value || '';
  else el.innerText = value || '';
  setByPath(model, key, editableValue(el));
  markTouched(key);
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); });
}
function findEditableByKey(key) {
  if (!key) return null;
  return document.querySelector(`[data-edit-key="${CSS.escape(key)}"]`);
}
function selectedEditable() {
  const active = document.activeElement?.closest?.('[data-edit-key]');
  if (active) return active;
  if (activeEditKey) return findEditableByKey(activeEditKey);
  return null;
}
function initialValueForKey(key) {
  const value = getByPath(initialPayload, key);
  if (value && typeof value === 'object' && 'html' in value) return value.html || '';
  return value ?? '';
}
function pushUndo(el, previousValue) {
  const key = el?.getAttribute('data-edit-key');
  if (!key) return;
  undoStack.push({key, value: previousValue});
  if (undoStack.length > 80) undoStack.shift();
}
function undoLastEdit() {
  const last = undoStack.pop();
  if (!last) return;
  const el = findEditableByKey(last.key);
  if (el) writeEditableValue(el, last.value);
}
function resetSelectedBlock() {
  const el = selectedEditable();
  if (!el) return;
  pushUndo(el, editableValue(el));
  writeEditableValue(el, String(initialValueForKey(el.getAttribute('data-edit-key')) ?? ''));
}
function replaceAllText() {
  const find = document.getElementById('findText')?.value || '';
  const repl = document.getElementById('replaceText')?.value || '';
  if (!find) return;
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const before = isHtmlEditKey(el.getAttribute('data-edit-key')) ? el.innerHTML : el.innerText;
    if (!before || !before.includes(find)) return;
    pushUndo(el, editableValue(el));
    if (isHtmlEditKey(el.getAttribute('data-edit-key'))) el.innerHTML = before.split(find).join(repl);
    else el.innerText = before.split(find).join(repl);
    markTouched(el.getAttribute('data-edit-key'));
  });
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); });
}
function notifyEditor(message) {
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = message;
    note.classList.add('show');
  }
}
function closestEditableBlock() {
  const selection = window.getSelection();
  let node = selection?.anchorNode || document.activeElement;
  if (node && node.nodeType === Node.TEXT_NODE) node = node.parentElement;
  const editable = node?.closest?.('[data-edit-key]') || selectedEditable();
  if (!editable) return null;
  const candidate = node?.closest?.('li,p,div,span') || editable;
  if (!editable.contains(candidate) && candidate !== editable) return editable;
  return candidate === editable ? editable : candidate;
}
const CONTROLLED_TEXT_STYLE_CLASSES = controlledPresetClassNames('text_styles');
const CONTROLLED_COLOR_CLASSES = controlledPresetClassNames('colors');
const CONTROLLED_SPACING_CLASSES = controlledPresetClassNames('spacing');

function isRichEditable(el) {
  return !!(el && isHtmlEditKey(el.getAttribute('data-edit-key') || ''));
}
function richEditableContext() {
  const editable = selectedEditable();
  if (!isRichEditable(editable)) {
    notifyEditor('Select a day or final-page content block first. Cover and title fields keep their fixed PDF styles.');
    return null;
  }
  return editable;
}
function commitEditableDomChange(editable) {
  const key = editable?.getAttribute('data-edit-key');
  if (!key) return;
  setByPath(model, key, editableValue(editable));
  markTouched(key);
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateEditorStats(); });
}
function removeClassGroup(node, classGroup) {
  classGroup.forEach(cls => node.classList?.remove(cls));
}
function selectedNodeInside(editable) {
  const selection = window.getSelection();
  let node = selection?.anchorNode || document.activeElement;
  if (node && node.nodeType === Node.TEXT_NODE) node = node.parentElement;
  if (node && editable.contains(node)) return node;
  return null;
}
function selectedStyleTarget(editable) {
  let node = selectedNodeInside(editable);
  let candidate = node?.closest?.('li,.body-text,.section-title,.row-type,.meta-line,p,span');
  if (candidate && candidate !== editable && editable.contains(candidate) && !candidate.classList.contains('source-row-marker')) return candidate;

  candidate = editable.querySelector('li,.body-text,.section-title,.row-type,.meta-line,p,span');
  if (candidate && !candidate.classList.contains('source-row-marker')) return candidate;

  const text = editable.textContent || '';
  if (text.trim() && !editable.children.length) {
    editable.innerHTML = `<div class="body-text">${esc(text.trim())}</div>`;
    return editable.querySelector('.body-text');
  }
  return null;
}
function applyClassPreset(className, classGroup) {
  const editable = richEditableContext();
  if (!editable) return;
  const target = selectedStyleTarget(editable);
  if (!target) {
    notifyEditor('Place the cursor in a text line first.');
    return;
  }
  pushUndo(editable, editableValue(editable));
  removeClassGroup(target, classGroup);
  if (className) target.classList.add(className);
  commitEditableDomChange(editable);
}
function applyTextStylePreset(preset) {
  const mapping = controlledPresetClassMap('text_styles');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_TEXT_STYLE_CLASSES);
}
function applyColorPreset(preset) {
  const mapping = controlledPresetClassMap('colors');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_COLOR_CLASSES);
}
function applySpacingPreset(preset) {
  const mapping = controlledPresetClassMap('spacing');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_SPACING_CLASSES);
}
function selectedTextToolEditable() {
  const el = selectedEditorElement() || selectedEditable();
  if (isRichEditable(el)) return el;
  const nested = el?.querySelector?.('[data-edit-key]');
  if (isRichEditable(nested)) return nested;
  return null;
}
function selectedTextToolTarget() {
  const editable = selectedTextToolEditable();
  if (!editable) return null;
  return selectedStyleTarget(editable);
}
function canUsePdfSafeTextTools() {
  return !!selectedTextToolEditable();
}
function clearSelectedFormatting() {
  const editable = selectedTextToolEditable();
  if (!editable) {
    notifyEditor('Select a rich text content block first. This keeps fixed cover/day-title PDF styles safe.');
    return;
  }
  const target = selectedStyleTarget(editable);
  if (!target) {
    notifyEditor('Place the cursor in a text line first.');
    return;
  }
  pushUndo(editable, editableValue(editable));
  removeClassGroup(target, CONTROLLED_TEXT_STYLE_CLASSES);
  removeClassGroup(target, CONTROLLED_COLOR_CLASSES);
  removeClassGroup(target, CONTROLLED_SPACING_CLASSES);
  commitEditableDomChange(editable);
  updateRightInspector();
}
function insertHtmlAtSelectionOrEnd(editable, html) {
  editable.focus();
  const selection = window.getSelection();
  if (selection && selection.rangeCount && editable.contains(selection.anchorNode)) {
    document.execCommand('insertHTML', false, html);
  } else {
    editable.insertAdjacentHTML('beforeend', html);
  }
}
function insertControlledBlock(html) {
  const editable = richEditableContext();
  if (!editable) return;
  pushUndo(editable, editableValue(editable));
  insertHtmlAtSelectionOrEnd(editable, html);
  commitEditableDomChange(editable);
}
function addNoteBlock() {
  insertControlledBlock(controlledBlockTemplate('note'));
}
function addDividerBlock() {
  insertControlledBlock(controlledBlockTemplate('divider'));
}
function plainTextToCleanPasteHtml(text) {
  const lines = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const chunks = [];
  let list = [];
  function flushList() {
    if (list.length) {
      chunks.push('<ul>' + list.map(item => `<li>${esc(item)}</li>`).join('') + '</ul>');
      list = [];
    }
  }
  lines.forEach(raw => {
    const line = raw.trim();
    if (!line) { flushList(); return; }
    const bullet = line.match(/^(?:[•\-*]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      list.push(bullet[1].trim());
    } else {
      flushList();
      chunks.push(`<div>${esc(line)}</div>`);
    }
  });
  flushList();
  return chunks.join('') || esc(text || '');
}
function sanitizeClipboardHtml(html, fallbackText) {
  if (!html || !String(html).trim()) return plainTextToCleanPasteHtml(fallbackText || '');
  const box = document.createElement('div');
  box.innerHTML = html;
  const allowedTags = new Set(['DIV','P','BR','UL','OL','LI','STRONG','B','EM','I','SPAN']);
  const allowedClasses = new Set([
    'section-title','row-type','strong-line','body-text','detail-list','final-list','inclusion-entry',
    'inclusion-entry-title','inclusion-entry-detail','inclusion-entry-spacer','meta-line','meta-label',
    'small-section','content-block','muted-note','inclusion-category-block','inclusion-category-list',
    'inclusion-multiline-list',
    ...controlledEditorAllowedClasses(),
  ]);
  box.querySelectorAll('*').forEach(node => {
    const tag = node.tagName;
    if (!allowedTags.has(tag)) {
      const parent = node.parentNode;
      while (node.firstChild) parent.insertBefore(node.firstChild, node);
      parent.removeChild(node);
      return;
    }
    const classes = node.classList ? Array.from(node.classList).filter(cls => allowedClasses.has(cls)) : [];
    Array.from(node.attributes).forEach(attr => node.removeAttribute(attr.name));
    if (classes.length) node.setAttribute('class', classes.join(' '));
  });
  const cleaned = box.innerHTML.trim();
  return cleaned || plainTextToCleanPasteHtml(fallbackText || '');
}
function insertCleanClipboardHtml(event) {
  event.preventDefault();
  const data = event.clipboardData || window.clipboardData;
  const html = sanitizeClipboardHtml(data?.getData('text/html') || '', data?.getData('text/plain') || '');
  document.execCommand('insertHTML', false, html);
}
function pageObjectAt(index) {
  const pages = Array.isArray(model.final_pages?.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
  if (index < 0 || index >= pages.length) return {pages, page: null};
  const page = typeof pages[index] === 'string' ? {html: pages[index]} : (pages[index] || {html: ''});
  pages[index] = page;
  return {pages, page};
}
function htmlTextContent(html) {
  const box = document.createElement('div');
  box.innerHTML = html || '';
  return (box.textContent || '').replace(/\s+/g, ' ').trim();
}
function stripEditorArtifactsFromHtml(html) {
  const box = document.createElement('div');
  box.innerHTML = html || '';
  box.querySelectorAll('*').forEach(node => {
    node.removeAttribute('style');
    node.removeAttribute('contenteditable');
    node.removeAttribute('data-edit-key');
    node.classList.remove('warning-hit');
  });
  return box.innerHTML;
}

function editorSlug(value) {
  const slug = String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return slug || 'page';
}
function documentPages() {
  if (!Array.isArray(model.document_pages)) model.document_pages = [];
  return model.document_pages;
}
function sortedDocumentPages() {
  return documentPages().slice().sort((a, b) => Number(a?.sort_order || 0) - Number(b?.sort_order || 0));
}
function documentPageById(pageId) {
  return documentPages().find(page => String(page?.page_id || '') === String(pageId || '')) || null;
}
function pageIndexById(pageId) {
  return documentPages().findIndex(page => String(page?.page_id || '') === String(pageId || ''));
}
function pageIsHidden(pageId) {
  return !!documentPageById(pageId)?.is_hidden;
}
function ensureDocumentPage(pageId, pageType, title, sortOrder, extras = {}) {
  const pages = documentPages();
  let page = documentPageById(pageId);
  if (!page) {
    page = Object.assign({
      page_id: pageId,
      page_type: pageType,
      title,
      sort_order: sortOrder,
      is_hidden: false,
      generated_blocks: [],
      manual_blocks: [],
      editable_fields: {},
      style_overrides: {},
      page_overrides: {},
      page_actions: {hide: true, restore: true, move: pageType === 'manual', duplicate: pageType === 'manual', reset: pageType !== 'manual'}
    }, extras || {});
    pages.push(page);
  } else {
    if (!page.title && title) page.title = title;
    if (!page.page_type && pageType) page.page_type = pageType;
    if (!page.sort_order) page.sort_order = sortOrder;
    if (!page.page_actions) page.page_actions = {hide: true, restore: true, move: pageType === 'manual', duplicate: pageType === 'manual', reset: pageType !== 'manual'};
  }
  return page;
}
function pageIdForDay(day, index) {
  const identity = String(day?.day || day?.day_id || day?.label || '').trim();
  const page = documentPages().find(page => {
    if (page?.page_type !== 'generated_day') return false;
    if (identity && String(page?.source_day_id || '') === identity) return true;
    if (identity && String(page?.title || '') === identity) return true;
    return Number(page?.sort_order || 0) === index + 3;
  });
  return page?.page_id || `day-${editorSlug(identity || `Day ${index + 1}`)}`;
}
function finalPageId(sectionId) {
  if (sectionId === 'whats_included') return 'final-whats-included';
  if (sectionId === 'whats_not_included') return 'final-whats-not-included';
  if (sectionId === 'important_travel_notes') return 'final-important-travel-notes';
  return `final-${editorSlug(sectionId)}`;
}

function humanizeEditorToken(value) {
  return String(value || '')
    .replace(/[_\-.]+/g, ' ')
    .replace(/\b\w/g, ch => ch.toUpperCase())
    .trim();
}
function contractPage(pageId) {
  return documentPages().find(page => String(page?.page_id || '') === String(pageId || '')) || null;
}
function contractBlock(page, blockId) {
  if (!page || !blockId) return null;
  const blocks = [...(page.generated_blocks || []), ...(page.manual_blocks || [])];
  return blocks.find(block => String(block?.block_id || '') === String(blockId || '')) || null;
}
function safeDayPageId(dayIndex) {
  const index = Number(dayIndex || 0);
  const day = Array.isArray(model?.days) ? model.days[index] : null;
  if (typeof pageIdForDay === 'function') return pageIdForDay(day || {}, index);
  return `day-${editorSlug(day?.day || day?.label || `Day ${index + 1}`)}`;
}
function finalPageIdForEditKey(key) {
  if (key.includes('whats_included')) return finalPageId('whats_included');
  if (key.includes('whats_not_included')) return finalPageId('whats_not_included');
  if (key.includes('important_travel_notes')) return finalPageId('important_travel_notes');
  return finalPageId('final');
}
function editorFieldLabel(key, explicitLabel = '') {
  if (explicitLabel) return explicitLabel;
  const tail = String(key || '').split('.').pop() || 'field';
  return humanizeEditorToken(tail);
}
function inferEditorBlockMetaForKey(key, label = '') {
  const editKey = String(key || '');
  const meta = {
    page_id: '',
    page_title: '',
    block_id: '',
    block_type: 'text',
    field_key: editKey,
    field_label: editorFieldLabel(editKey, label),
    source_row_ids: [],
    validation_status: 'unknown',
  };
  let match = editKey.match(/^document_pages\.(\d+)\.manual_blocks\.(\d+)\.editable_fields\.(.+)$/);
  if (match) {
    const page = documentPages()[Number(match[1])] || {};
    const block = (page.manual_blocks || [])[Number(match[2])] || {};
    meta.page_id = page.page_id || '';
    meta.page_title = page.title || 'Manual page';
    meta.block_id = block.block_id || `${meta.page_id}__manual-${Number(match[2]) + 1}`;
    meta.block_type = block.block_type || 'manual_text';
    meta.source_row_ids = block.source_row_ids || [];
    meta.validation_status = block.validation_status || page.validation_status || 'unknown';
    return meta;
  }
  match = editKey.match(/^document_pages\.(\d+)\.title$/);
  if (match) {
    const page = documentPages()[Number(match[1])] || {};
    meta.page_id = page.page_id || '';
    meta.page_title = page.title || 'Manual page';
    meta.block_id = `${meta.page_id || 'manual'}__title`;
    meta.block_type = 'page_title';
    meta.source_row_ids = page.source_row_ids || [];
    meta.validation_status = page.validation_status || 'unknown';
    return meta;
  }
  match = editKey.match(/^days\.(\d+)\.(.+)$/);
  if (match) {
    const dayIndex = Number(match[1]);
    const field = match[2];
    const pageId = safeDayPageId(dayIndex);
    const page = contractPage(pageId) || {};
    const blockId = field === 'blocks_html' ? `${pageId}__main` : `${pageId}__${editorSlug(field)}`;
    const block = contractBlock(page, blockId) || contractBlock(page, `${pageId}__main`) || {};
    meta.page_id = pageId;
    meta.page_title = page.title || model?.days?.[dayIndex]?.day || `Day ${dayIndex + 1}`;
    meta.block_id = blockId;
    meta.block_type = field === 'blocks_html' ? (block.block_type || 'day_content') : 'day_field';
    meta.source_row_ids = block.source_row_ids || page.source_row_ids || [];
    meta.validation_status = block.validation_status || page.validation_status || 'unknown';
    return meta;
  }
  if (editKey.startsWith('cover.')) {
    const field = editKey.slice('cover.'.length);
    const page = contractPage('cover') || {};
    meta.page_id = 'cover';
    meta.page_title = page.title || 'Cover';
    meta.block_id = `cover__${editorSlug(field)}`;
    meta.block_type = field.includes('image') ? 'image' : 'cover_field';
    meta.source_row_ids = page.source_row_ids || [];
    meta.validation_status = page.validation_status || 'unknown';
    return meta;
  }
  if (editKey.startsWith('summary.')) {
    const page = contractPage('summary') || {};
    const field = editKey.slice('summary.'.length);
    meta.page_id = 'summary';
    meta.page_title = page.title || 'Trip summary';
    meta.block_id = `summary__${editorSlug(field)}`;
    meta.block_type = 'summary_field';
    meta.source_row_ids = page.source_row_ids || [];
    meta.validation_status = page.validation_status || 'unknown';
    return meta;
  }
  if (editKey.startsWith('final_pages.')) {
    const pageId = finalPageIdForEditKey(editKey);
    const page = contractPage(pageId) || {};
    const block = contractBlock(page, `${pageId}__main`) || {};
    meta.page_id = pageId;
    meta.page_title = page.title || 'Final section';
    meta.block_id = `${pageId}__main`;
    meta.block_type = block.block_type || 'final_section';
    meta.source_row_ids = block.source_row_ids || page.source_row_ids || [];
    meta.validation_status = block.validation_status || page.validation_status || 'unknown';
    return meta;
  }
  return meta;
}
function editorBlockAttrs(key, label = '') {
  const meta = inferEditorBlockMetaForKey(key, label);
  return ` data-editor-page-id="${escAttr(meta.page_id)}" data-editor-block-id="${escAttr(meta.block_id)}" data-editor-block-type="${escAttr(meta.block_type)}" data-editor-field-key="${escAttr(meta.field_key)}" data-editor-field-label="${escAttr(meta.field_label)}"`;
}
function selectEditorPage(pageId) {
  activePageId = pageId;
  activeBlockId = null;
  activeFieldKey = null;
  updateSelectionUi();
  updateRightInspector();
}
function selectEditorBlockFromElement(el) {
  const target = el?.closest?.('[data-editor-block-id]') || el?.closest?.('[data-edit-key]');
  if (!target) return;
  const meta = inferEditorBlockMetaForKey(target.getAttribute('data-editor-field-key') || target.getAttribute('data-edit-key') || '', target.getAttribute('data-editor-field-label') || '');
  activePageId = target.getAttribute('data-editor-page-id') || meta.page_id || target.closest('[data-page-id]')?.getAttribute('data-page-id') || activePageId;
  activeBlockId = target.getAttribute('data-editor-block-id') || meta.block_id || '';
  activeFieldKey = target.getAttribute('data-editor-field-key') || target.getAttribute('data-edit-key') || '';
  updateSelectionUi();
  updateRightInspector();
}
function selectedEditorElement() {
  if (activeFieldKey) {
    const byField = document.querySelector(`[data-editor-field-key="${CSS.escape(activeFieldKey)}"]`) || document.querySelector(`[data-edit-key="${CSS.escape(activeFieldKey)}"]`);
    if (byField) return byField;
  }
  if (activeBlockId) return document.querySelector(`[data-editor-block-id="${CSS.escape(activeBlockId)}"]`);
  return selectedEditable();
}
function updateSelectionUi() {
  document.querySelectorAll('[data-page-id]').forEach(el => el.classList.toggle('selected-page', el.getAttribute('data-page-id') === activePageId));
  document.querySelectorAll('[data-outline-page-id]').forEach(el => el.classList.toggle('active', el.getAttribute('data-outline-page-id') === activePageId));
  document.querySelectorAll('[data-editor-block-id]').forEach(el => {
    const blockMatch = activeBlockId && el.getAttribute('data-editor-block-id') === activeBlockId;
    const fieldMatch = activeFieldKey && (el.getAttribute('data-editor-field-key') === activeFieldKey || el.getAttribute('data-edit-key') === activeFieldKey);
    el.classList.toggle('selected-editor-block', !!(blockMatch && (!activeFieldKey || fieldMatch)));
  });
}
function pageInspectorRows(page) {
  const fields = Object.keys(page?.editable_fields || {});
  const rows = fields.slice(0, 10).map(field => `<li>${esc(humanizeEditorToken(field))}</li>`).join('');
  return rows || '<li>No direct editable fields exposed yet</li>';
}
function selectedInspectorMeta() {
  const el = selectedEditorElement();
  const fieldKey = activeFieldKey || el?.getAttribute?.('data-editor-field-key') || el?.getAttribute?.('data-edit-key') || '';
  const meta = inferEditorBlockMetaForKey(fieldKey, el?.getAttribute?.('data-editor-field-label') || '');
  const page = contractPage(activePageId || meta.page_id) || {};
  const block = contractBlock(page, activeBlockId || meta.block_id) || {};
  return {el, fieldKey, meta, page, block};
}
function renderSourceRows(sourceRowIds) {
  const ids = Array.isArray(sourceRowIds) ? sourceRowIds : [];
  if (!ids.length) return '<span class="empty-source">No source rows linked</span>';
  return ids.slice(0, 8).map(id => `<span class="source-chip">${esc(id)}</span>`).join('');
}
function renderInspectorTextTools(hasBlock) {
  const canStyle = hasBlock && canUsePdfSafeTextTools();
  const disabled = canStyle ? '' : 'disabled';
  const hint = canStyle
    ? 'These controls write controlled classes into the selected rich text block, so preview and PDF stay aligned.'
    : 'Select a day content, final-section, or manual-page rich text block. Fixed fields stay editable, but keep their locked PDF styles for now.';
  return `<div class="inspector-card text-tools-card"><div class="inspector-kicker">Text tools</div>
    <label class="inspector-control-label" for="inspectorTextStylePreset">Paragraph style</label>
    <select id="inspectorTextStylePreset" ${disabled} aria-label="Inspector paragraph style">${controlledPresetOptionsHtml('text_styles', 'Choose style')}</select>
    <label class="inspector-control-label" for="inspectorColorPreset">Color / highlight</label>
    <select id="inspectorColorPreset" ${disabled} aria-label="Inspector color preset">${controlledPresetOptionsHtml('colors', 'Choose color')}</select>
    <div class="inspector-button-grid">
      <button type="button" class="ghost" id="inspectorCompactSpacingBtn" ${disabled}>Compact</button>
      <button type="button" class="ghost" id="inspectorNormalSpacingBtn" ${disabled}>Normal spacing</button>
      <button type="button" class="ghost" id="inspectorClearFormattingBtn" ${disabled}>Clear formatting</button>
    </div>
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorAddNoteBlockBtn" ${disabled}>Add note</button>
      <button type="button" class="ghost" id="inspectorAddDividerBtn" ${disabled}>Add divider</button>
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
  notifyEditor(action === 'focus' ? 'Image crop updated' : 'Image selection updated');
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
  return `<div class="inspector-card image-tools-card"><div class="inspector-kicker">Image tools</div>
    <strong>${esc(ctx.label)}</strong>
    <dl><dt>Mode</dt><dd>${esc(imageModeLabel(image))}</dd><dt>Name</dt><dd>${esc(image.name || image.auto_name || '—')}</dd><dt>Path</dt><dd>${esc(image.path || 'Automatic/default')}</dd></dl>
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

function renderRightInspector() {
  const {fieldKey, meta, page, block} = selectedInspectorMeta();
  const pageTitle = page?.title || meta.page_title || 'No page selected';
  const pageType = pageTypeLabel(page || {page_type: meta.block_type});
  const hasBlock = !!(fieldKey || activeBlockId);
  const sourceRows = block?.source_row_ids || meta.source_row_ids || page?.source_row_ids || [];
  const blockFields = Object.keys(block?.editable_fields || {});
  const selectedFieldHtml = hasBlock
    ? `<div class="inspector-card selected"><div class="inspector-kicker">Selected block</div><strong>${esc(meta.field_label || block.title || 'Editable field')}</strong><dl><dt>Type</dt><dd>${esc(humanizeEditorToken(block.block_type || meta.block_type))}</dd><dt>Field</dt><dd>${esc(fieldKey || '—')}</dd><dt>Block ID</dt><dd>${esc(activeBlockId || meta.block_id || '—')}</dd></dl></div>`
    : `<div class="inspector-card empty"><strong>Select text, an image, or a page</strong><p>Click any editable block on the canvas to inspect its source, page, and text controls.</p></div>`;
  const fieldList = blockFields.length
    ? blockFields.map(field => `<li>${esc(humanizeEditorToken(field))}</li>`).join('')
    : pageInspectorRows(page);
  return `<aside class="right-inspector" aria-label="Selected block inspector">
    <div class="inspector-title"><strong>Inspector</strong><span>${hasBlock ? 'Block' : 'Page'}</span></div>
    <div class="inspector-card"><div class="inspector-kicker">Page</div><strong>${esc(pageTitle)}</strong><dl><dt>Type</dt><dd>${esc(pageType)}</dd><dt>Page ID</dt><dd>${esc(page?.page_id || meta.page_id || '—')}</dd></dl></div>
    ${selectedFieldHtml}
    ${renderInspectorTextTools(hasBlock)}
    ${renderInspectorImageTools(fieldKey)}
    <div class="inspector-card"><div class="inspector-kicker">Editable fields</div><ul class="inspector-list">${fieldList}</ul></div>
    <div class="inspector-card"><div class="inspector-kicker">Source</div><div class="source-chip-list">${renderSourceRows(sourceRows)}</div></div>
    <div class="inspector-card"><div class="inspector-kicker">Actions</div><div class="inspector-actions"><button type="button" class="ghost" id="inspectorResetFieldBtn" ${hasBlock ? '' : 'disabled'}>Reset selected field</button><button type="button" class="ghost" id="inspectorFlagIssueBtn" ${hasBlock ? '' : 'disabled'}>Flag issue</button><button type="button" class="ghost" id="inspectorClearSelectionBtn" ${hasBlock || activePageId ? '' : 'disabled'}>Clear selection</button></div></div>
    <p class="inspector-hint">Layout controls will plug into this same selected block contract next.</p>
  </aside>`;
}
function updateRightInspector() {
  const inspector = document.querySelector('.right-inspector');
  if (!inspector) return;
  inspector.outerHTML = renderRightInspector();
  attachInspectorHandlers();
  requestAnimationFrame(() => Streamlit.setFrameHeight(document.body.scrollHeight + 20));
}
function attachInspectorHandlers() {
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
  document.getElementById('inspectorAddNoteBlockBtn')?.addEventListener('click', () => { addNoteBlock(); updateRightInspector(); });
  document.getElementById('inspectorAddDividerBtn')?.addEventListener('click', () => { addDividerBlock(); updateRightInspector(); });
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
  document.getElementById('inspectorResetFieldBtn')?.addEventListener('click', resetSelectedBlock);
  document.getElementById('inspectorFlagIssueBtn')?.addEventListener('click', flagSelectedIssue);
  document.getElementById('inspectorClearSelectionBtn')?.addEventListener('click', () => {
    activeBlockId = null;
    activeFieldKey = null;
    updateSelectionUi();
    updateRightInspector();
  });
}
function maxDocumentPageOrder() {
  return sortedDocumentPages().reduce((max, page) => Math.max(max, Number(page?.sort_order || 0)), 0);
}
function markDocumentPagesTouched(message = 'Page list updated') {
  markTouched('document_pages');
  notifyEditor(message);
}
function hideDocumentPage(pageId) {
  collect();
  const page = documentPageById(pageId);
  if (!page) return;
  page.is_hidden = true;
  if (activePageId === pageId) activePageId = null;
  markDocumentPagesTouched(page.page_type === 'manual' ? 'Manual page hidden' : 'Page hidden from itinerary');
  draw();
}
function restoreDocumentPage(pageId) {
  collect();
  const page = documentPageById(pageId);
  if (!page) return;
  page.is_hidden = false;
  activePageId = pageId;
  markDocumentPagesTouched('Page restored');
  draw();
  scrollToPage(pageId);
}
function addManualPage() {
  collect();
  const pageId = `manual-${Date.now()}`;
  const blockId = `${pageId}__main`;
  const page = {
    page_id: pageId,
    page_type: 'manual',
    title: 'Blank page',
    sort_order: maxDocumentPageOrder() + 1,
    is_hidden: false,
    source_day_id: '',
    source_section_id: '',
    source_row_ids: [],
    editable_fields: {title: 'Blank page'},
    generated_blocks: [],
    manual_blocks: [{
      block_id: blockId,
      block_type: 'manual_text',
      title: 'Manual text',
      editable_fields: {content_html: '<div class="body-text">New page text</div>'},
      style_overrides: {},
      image_binding: {},
      source_row_ids: [],
      dirty_state: 'dirty',
      validation_status: 'unknown'
    }],
    style_overrides: {},
    page_overrides: {},
    page_actions: {hide: true, restore: true, move: true, duplicate: true, reset: false},
    validation_status: 'unknown'
  };
  documentPages().push(page);
  activePageId = pageId;
  markDocumentPagesTouched('Blank page added');
  draw();
  scrollToPage(pageId);
}
function duplicateManualPage(pageId) {
  collect();
  const original = documentPageById(pageId);
  if (!original || original.page_type !== 'manual') return;
  const clone = JSON.parse(JSON.stringify(original));
  const newId = `manual-${Date.now()}`;
  clone.page_id = newId;
  clone.title = `${original.title || 'Blank page'} copy`;
  clone.sort_order = Number(original.sort_order || maxDocumentPageOrder()) + 0.5;
  clone.is_hidden = false;
  (clone.manual_blocks || []).forEach((block, idx) => { block.block_id = `${newId}__manual-${idx + 1}`; });
  documentPages().push(clone);
  activePageId = newId;
  markDocumentPagesTouched('Manual page duplicated');
  draw();
  scrollToPage(newId);
}
function moveManualPage(pageId, direction) {
  collect();
  const pages = sortedDocumentPages();
  const current = pages.find(page => page.page_id === pageId);
  if (!current || current.page_type !== 'manual') return;
  const currentIndex = pages.findIndex(page => page.page_id === pageId);
  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= pages.length) return;
  const target = pages[targetIndex];
  const currentOrder = Number(current.sort_order || currentIndex + 1);
  current.sort_order = Number(target.sort_order || targetIndex + 1);
  target.sort_order = currentOrder;
  activePageId = pageId;
  markDocumentPagesTouched('Manual page moved');
  draw();
  scrollToPage(pageId);
}
function scrollToPage(pageId) {
  selectEditorPage(pageId);
  requestAnimationFrame(() => {
    const target = document.querySelector(`[data-page-id="${CSS.escape(pageId)}"]`);
    if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
    updateSelectionUi();
  });
}
function pageChrome(pageId, label, bodyHtml, options = {}) {
  const page = ensureDocumentPage(pageId, options.pageType || 'generated', label, options.sortOrder || 999, options.extras || {});
  const isHidden = !!page.is_hidden;
  const canMove = page.page_type === 'manual';
  const controls = `<div class="page-controls"><button class="ghost" type="button" data-outline-page-id="${escAttr(pageId)}">Select</button>${isHidden ? `<button class="ghost" type="button" data-doc-page-action="restore" data-page-id-ref="${escAttr(pageId)}">Restore</button>` : `<button class="danger" type="button" data-doc-page-action="hide" data-page-id-ref="${escAttr(pageId)}">Delete page</button>`}${canMove ? `<button class="ghost" type="button" data-doc-page-action="move-up" data-page-id-ref="${escAttr(pageId)}">Move up</button><button class="ghost" type="button" data-doc-page-action="move-down" data-page-id-ref="${escAttr(pageId)}">Move down</button><button class="ghost" type="button" data-doc-page-action="duplicate" data-page-id-ref="${escAttr(pageId)}">Duplicate</button>` : ''}</div>`;
  if (isHidden) return '';
  return `<div class="page-wrap ${activePageId === pageId ? 'selected-page' : ''}" data-page-id="${escAttr(pageId)}"><div class="page-header-row"><div class="page-label">${esc(label)}</div>${controls}</div>${bodyHtml}</div>`;
}

function deleteInclusionPage(index) {
  collect();
  if (!model.final_pages) model.final_pages = {};
  const {pages, page} = pageObjectAt(index);
  if (!pages.length || !page) return;
  const pageText = htmlTextContent(page.html || '');
  if (pageText) {
    notifyEditor('Page still has content — move content up or clear it before removing the page.');
    return;
  }
  pages.splice(index, 1);
  model.final_pages.whats_included_pages_html = pages.length ? pages : [{html: ''}];
  markTouched('final_pages.whats_included_pages_html');
  draw();
}
function mergeInclusionPageUp(index) {
  collect();
  if (!model.final_pages) model.final_pages = {};
  const pages = Array.isArray(model.final_pages.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
  if (index <= 0 || index >= pages.length) return;
  const previous = typeof pages[index - 1] === 'string' ? {html: pages[index - 1]} : (pages[index - 1] || {html: ''});
  const current = typeof pages[index] === 'string' ? {html: pages[index]} : (pages[index] || {html: ''});
  const previousHtml = stripEditorArtifactsFromHtml(previous.html || '');
  const currentHtml = stripEditorArtifactsFromHtml(current.html || '');
  if (!htmlTextContent(currentHtml)) {
    notifyEditor('Nothing to move from this page.');
    return;
  }
  previous.html = `${previousHtml}${previousHtml && currentHtml ? '<div class="inclusion-entry-spacer"></div>' : ''}${currentHtml}`;
  pages[index - 1] = previous;
  pages.splice(index, 1);
  model.final_pages.whats_included_pages_html = pages;
  markTouched('final_pages.whats_included_pages_html');
  draw();
}
function flagSelectedIssue() {
  const el = selectedEditable();
  if (!el) return;
  const key = el.getAttribute('data-edit-key');
  const flag = {
    key,
    label: el.closest('.page-wrap')?.querySelector('.page-label')?.innerText || '',
    original: String(initialValueForKey(key) ?? ''),
    corrected: editableValue(el),
  };
  if (!Array.isArray(model.issue_flags)) model.issue_flags = [];
  model.issue_flags.push(flag);
  markTouched('issue_flags');
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = 'Issue flagged';
    note.classList.add('show');
  }
}
function highlightWarnings() {
  let count = 0;
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const text = el.innerText || '';
    const hit = WARNING_PATTERNS.some(pattern => pattern.test(text));
    el.classList.toggle('warning-hit', hit);
    if (hit) count += 1;
  });
  const serverWarnings = Array.isArray(model.client_output_warnings) ? model.client_output_warnings.length : 0;
  const warningCount = document.getElementById('warningCount');
  if (warningCount) warningCount.textContent = `${Math.max(count, serverWarnings)} warnings`;
}
function updateEditorStats() {
  const editCount = document.getElementById('editCount');
  if (editCount) editCount.textContent = `${touchedKeys.size} manual edits pending`;
  highlightWarnings();
}

