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
function generatedValueForKey(key) {
  const generated = model?.generated_values || initialPayload?.generated_values || {};
  const value = getByPath(generated, key);
  if (value && typeof value === 'object' && 'html' in value) return value.html || '';
  return value;
}
function restoreValueForKey(key) {
  const generated = generatedValueForKey(key);
  if (generated !== undefined && generated !== null) return generated;
  return initialValueForKey(key);
}
function compareTextForValue(value, kind = '') {
  const raw = value === undefined || value === null ? '' : String(value);
  return (kind === 'html' || isHtmlEditKey(kind) ? htmlTextContent(raw) : raw)
    .replace(/\s+/g, ' ')
    .trim();
}
function fieldDiffState(key) {
  const kind = fieldKindForKey(key);
  if (!key || kind === 'image') return {hasGenerated: false, changed: false, current: '', generated: ''};
  const generated = generatedValueForKey(key);
  const hasGenerated = generated !== undefined && generated !== null;
  const current = inspectorFieldValue(key);
  const currentText = compareTextForValue(current, kind);
  const generatedText = compareTextForValue(hasGenerated ? generated : '', kind);
  return {hasGenerated, changed: hasGenerated && currentText !== generatedText, current, generated: hasGenerated ? generated : ''};
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
function renumberDocumentPageOrders(orderedPages = null) {
  const ordered = orderedPages || sortedDocumentPages();
  ordered.forEach((page, index) => {
    if (page) page.sort_order = index + 1;
  });
  return ordered;
}
function documentPageCanMove(page) {
  return !!page && page.is_hidden !== true;
}
function documentPageCanDuplicate(page) {
  return !!page && page.page_type === 'manual' && page.is_hidden !== true;
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
      page_actions: {hide: true, restore: true, move: true, duplicate: pageType === 'manual', reset: pageType !== 'manual'}
    }, extras || {});
    pages.push(page);
  } else {
    if (!page.title && title) page.title = title;
    if (!page.page_type && pageType) page.page_type = pageType;
    if (!page.sort_order) page.sort_order = sortOrder;
    if (!page.page_actions) page.page_actions = {hide: true, restore: true, move: true, duplicate: pageType === 'manual', reset: pageType !== 'manual'};
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
function ensurePageOverrides(page) {
  if (!page.page_overrides || typeof page.page_overrides !== 'object') page.page_overrides = {};
  return page.page_overrides;
}
function ensureBlockStyleOverrides(block) {
  if (!block.style_overrides || typeof block.style_overrides !== 'object') block.style_overrides = {};
  return block.style_overrides;
}
function selectedPageContract() {
  const {meta} = selectedInspectorMeta();
  return contractPage(activePageId || meta.page_id) || null;
}
function selectedBlockContract() {
  const {meta, page} = selectedInspectorMeta();
  return contractBlock(page, activeBlockId || meta.block_id) || null;
}
function manualBlockContextFromSelection() {
  const {fieldKey} = selectedInspectorMeta();
  const match = String(fieldKey || '').match(/^document_pages\.(\d+)\.manual_blocks\.(\d+)\./);
  if (!match) return null;
  const pageIndex = Number(match[1]);
  const blockIndex = Number(match[2]);
  const page = documentPages()[pageIndex];
  if (!page || page.page_type !== 'manual') return null;
  const block = Array.isArray(page.manual_blocks) ? page.manual_blocks[blockIndex] : null;
  if (!block) return null;
  return {page, pageIndex, block, blockIndex};
}

function manualPageTemplateCatalog() {
  return {
    blank: {
      label: 'Blank page',
      title: 'Blank page',
      blocks: [{type: 'manual_text', title: 'Manual text', html: '<div class="body-text">New page text</div>'}]
    },
    text: {
      label: 'Text page',
      title: 'Custom text page',
      blocks: [
        {type: 'manual_heading', title: 'Heading', html: '<div class="section-title">Add a heading</div>'},
        {type: 'manual_text', title: 'Body text', html: '<div class="body-text">Write your custom itinerary text here.</div>'}
      ]
    },
    image: {
      label: 'Image page',
      title: 'Custom image page',
      blocks: [
        {type: 'manual_heading', title: 'Image heading', html: '<div class="section-title">Image page</div>'},
        {type: 'manual_image', title: 'Image placeholder', html: '<div class="content-block"><div class="body-text"><strong>Image placeholder:</strong> Replace this text with image notes, a caption, or destination context.</div></div>'},
        {type: 'manual_text', title: 'Caption', html: '<div class="body-text">Add caption or supporting text.</div>'}
      ]
    },
    notes: {
      label: 'Notes page',
      title: 'Notes',
      blocks: [
        {type: 'manual_heading', title: 'Notes heading', html: '<div class="section-title">Notes</div>'},
        {type: 'manual_note', title: 'Notes list', html: '<ul class="final-list"><li>Add note one</li><li>Add note two</li></ul>'}
      ]
    },
    divider: {
      label: 'Divider page',
      title: 'Section divider',
      blocks: [
        {type: 'manual_heading', title: 'Divider heading', html: '<div class="section-title">Section title</div>'},
        {type: 'manual_text', title: 'Divider subtitle', html: '<div class="body-text">Add a short divider subtitle or introduction.</div>'}
      ]
    },
    info: {
      label: 'Info page',
      title: 'Practical information',
      blocks: [
        {type: 'manual_heading', title: 'Info heading', html: '<div class="section-title">Practical information</div>'},
        {type: 'manual_info', title: 'Information list', html: '<ul class="final-list"><li>Meeting point:</li><li>What to bring:</li><li>Important contact:</li></ul>'}
      ]
    }
  };
}
function manualPageTemplateOptionsHtml(selected = 'blank') {
  const catalog = manualPageTemplateCatalog();
  return Object.keys(catalog).map(templateId => `<option value="${escAttr(templateId)}" ${templateId === selected ? 'selected' : ''}>${esc(catalog[templateId].label)}</option>`).join('');
}
function manualBlockTemplateOptionsHtml(selected = 'text') {
  const catalog = manualPageTemplateCatalog();
  const blockOptions = [
    ['text', 'Text block'],
    ['heading', 'Heading block'],
    ['note', 'Note/list block'],
    ['divider', 'Divider text block'],
    ['image', 'Image placeholder block'],
    ['info', 'Info list block'],
  ];
  return blockOptions.map(([templateId, label]) => `<option value="${escAttr(templateId)}" ${templateId === selected ? 'selected' : ''}>${esc(label)}</option>`).join('');
}
function manualBlockTemplate(templateId) {
  const templates = {
    text: {type: 'manual_text', title: 'Text block', html: '<div class="body-text">New text block</div>'},
    heading: {type: 'manual_heading', title: 'Heading block', html: '<div class="section-title">New heading</div>'},
    note: {type: 'manual_note', title: 'Note/list block', html: '<ul class="final-list"><li>Add note</li></ul>'},
    divider: {type: 'manual_text', title: 'Divider text block', html: '<div class="body-text">Add divider text</div>'},
    image: {type: 'manual_image', title: 'Image placeholder', html: '<div class="content-block"><div class="body-text"><strong>Image placeholder:</strong> Add image notes or caption text.</div></div>'},
    info: {type: 'manual_info', title: 'Info list block', html: '<ul class="final-list"><li>Important detail:</li></ul>'},
  };
  return templates[templateId] || templates.text;
}
function createManualBlock(pageId, blockTemplate, blockIndex) {
  const template = blockTemplate || manualBlockTemplate('text');
  return {
    block_id: `${pageId}__${template.type || 'manual'}-${Date.now()}-${blockIndex + 1}`,
    block_type: template.type || 'manual_text',
    title: template.title || `Manual block ${blockIndex + 1}`,
    editable_fields: {content_html: template.html || '<div class="body-text">New content</div>'},
    style_overrides: {},
    image_binding: {},
    source_row_ids: [],
    dirty_state: 'dirty',
    validation_status: 'unknown'
  };
}
function manualPageFromTemplate(templateId = 'blank') {
  const catalog = manualPageTemplateCatalog();
  const template = catalog[templateId] || catalog.blank;
  const pageId = `manual-${templateId}-${Date.now()}`;
  const manualBlocks = (template.blocks || catalog.blank.blocks).map((blockTemplate, blockIndex) => createManualBlock(pageId, blockTemplate, blockIndex));
  return {
    page_id: pageId,
    page_type: 'manual',
    title: template.title || 'Custom page',
    sort_order: maxDocumentPageOrder() + 1,
    is_hidden: false,
    source_day_id: '',
    source_section_id: '',
    source_row_ids: [],
    editable_fields: {title: template.title || 'Custom page', template_id: templateId},
    generated_blocks: [],
    manual_blocks: manualBlocks,
    style_overrides: {},
    page_overrides: {template_id: templateId},
    page_actions: {hide: true, restore: true, move: true, duplicate: true, reset: false},
    validation_status: 'unknown'
  };
}
function pageLayoutClasses(page) {
  const overrides = page?.page_overrides || {};
  const density = String(overrides.spacing_density || 'standard').replace(/[^a-z0-9_-]/gi, '') || 'standard';
  const classes = [`layout-density-${density}`];
  if (overrides.keep_page_together) classes.push('layout-keep-page-together');
  return classes.join(' ');
}
function blockLayoutClasses(block) {
  const overrides = block?.style_overrides || {};
  const density = String(overrides.spacing_density || '').replace(/[^a-z0-9_-]/gi, '');
  const classes = [];
  if (density) classes.push(`layout-density-${density}`);
  if (overrides.keep_block_together) classes.push('layout-keep-block-together');
  return classes.join(' ');
}
function setSelectedPageOverride(name, value) {
  const page = selectedPageContract();
  if (!page) { notifyEditor('Select a page first.'); return; }
  collect();
  const overrides = ensurePageOverrides(page);
  if (value === '' || value === null || value === undefined || value === false) delete overrides[name];
  else overrides[name] = value;
  markDocumentPagesTouched('Page layout updated');
  draw();
  scrollToPage(page.page_id);
}
function resetSelectedPageLayout() {
  const page = selectedPageContract();
  if (!page) { notifyEditor('Select a page first.'); return; }
  collect();
  page.page_overrides = {};
  markDocumentPagesTouched('Page layout reset');
  draw();
  scrollToPage(page.page_id);
}
function setSelectedBlockOverride(name, value) {
  const page = selectedPageContract();
  const block = selectedBlockContract();
  if (!page || !block) { notifyEditor('Select a block first.'); return; }
  collect();
  const overrides = ensureBlockStyleOverrides(block);
  if (value === '' || value === null || value === undefined || value === false) delete overrides[name];
  else overrides[name] = value;
  markDocumentPagesTouched('Block layout updated');
  draw();
  scrollToPage(page.page_id);
}
function addManualBlockToSelectedPage(templateId = 'text') {
  const page = selectedPageContract();
  if (!page || page.page_type !== 'manual') { notifyEditor('Select a manual page first.'); return; }
  collect();
  if (!Array.isArray(page.manual_blocks)) page.manual_blocks = [];
  const blockIndex = page.manual_blocks.length;
  const block = createManualBlock(page.page_id, manualBlockTemplate(templateId), blockIndex);
  page.manual_blocks.push(block);
  activePageId = page.page_id;
  activeBlockId = block.block_id;
  activeFieldKey = `document_pages.${pageIndexById(page.page_id)}.manual_blocks.${blockIndex}.editable_fields.content_html`;
  markDocumentPagesTouched(`${manualBlockTemplate(templateId).title || 'Manual block'} added`);
  draw();
  scrollToPage(page.page_id);
}
function addManualTextBlockToSelectedPage() {
  addManualBlockToSelectedPage('text');
}
function duplicateSelectedManualBlock() {
  const ctx = manualBlockContextFromSelection();
  if (!ctx) { notifyEditor('Select a manual text block first.'); return; }
  collect();
  const clone = JSON.parse(JSON.stringify(ctx.block));
  clone.block_id = `${ctx.page.page_id}__manual-${Date.now()}`;
  clone.title = `${ctx.block.title || 'Manual text'} copy`;
  ctx.page.manual_blocks.splice(ctx.blockIndex + 1, 0, clone);
  activeBlockId = clone.block_id;
  activeFieldKey = `document_pages.${ctx.pageIndex}.manual_blocks.${ctx.blockIndex + 1}.editable_fields.content_html`;
  markDocumentPagesTouched('Manual text block duplicated');
  draw();
  scrollToPage(ctx.page.page_id);
}
function moveSelectedManualBlock(direction) {
  const ctx = manualBlockContextFromSelection();
  if (!ctx) { notifyEditor('Select a manual text block first.'); return; }
  collect();
  const targetIndex = ctx.blockIndex + direction;
  if (targetIndex < 0 || targetIndex >= ctx.page.manual_blocks.length) return;
  const blocks = ctx.page.manual_blocks;
  [blocks[ctx.blockIndex], blocks[targetIndex]] = [blocks[targetIndex], blocks[ctx.blockIndex]];
  activeBlockId = blocks[targetIndex].block_id;
  activeFieldKey = `document_pages.${ctx.pageIndex}.manual_blocks.${targetIndex}.editable_fields.content_html`;
  markDocumentPagesTouched('Manual text block moved');
  draw();
  scrollToPage(ctx.page.page_id);
}
function moveManualBlockToIndex(pageId, fromIndex, targetIndex) {
  collect();
  const page = documentPageById(pageId);
  if (!page || page.page_type !== 'manual' || !Array.isArray(page.manual_blocks)) return;
  const from = Number(fromIndex);
  const to = Math.max(0, Math.min(Number(targetIndex), page.manual_blocks.length - 1));
  if (!Number.isFinite(from) || from < 0 || from >= page.manual_blocks.length || from === to) return;
  const [block] = page.manual_blocks.splice(from, 1);
  page.manual_blocks.splice(to, 0, block);
  activePageId = page.page_id;
  activeBlockId = block.block_id || '';
  const pageIndex = pageIndexById(page.page_id);
  activeFieldKey = `document_pages.${pageIndex}.manual_blocks.${to}.editable_fields.content_html`;
  markDocumentPagesTouched('Manual block order updated');
  draw();
  scrollToPage(page.page_id);
}

function deleteSelectedManualBlock() {
  const ctx = manualBlockContextFromSelection();
  if (!ctx) { notifyEditor('Select a manual text block first.'); return; }
  collect();
  if (ctx.page.manual_blocks.length <= 1) {
    ctx.block.editable_fields = {content_html: ''};
    notifyEditor('Last manual text block cleared');
  } else {
    ctx.page.manual_blocks.splice(ctx.blockIndex, 1);
    notifyEditor('Manual text block removed');
  }
  activeBlockId = null;
  activeFieldKey = null;
  activePageId = ctx.page.page_id;
  markTouched('document_pages');
  draw();
  scrollToPage(ctx.page.page_id);
}
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

function renderInspectorLayoutTools(hasBlock, page, block) {
  const hasPage = !!(page && page.page_id);
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
  return `<div class="inspector-card layout-tools-card"><div class="inspector-kicker">Layout tools</div>
    <label class="inspector-control-label" for="inspectorManualPageTemplate">Add page template</label>
    <select id="inspectorManualPageTemplate" aria-label="Manual page template">${manualPageTemplateOptionsHtml('blank')}</select>
    <button type="button" class="ghost full-width" id="inspectorAddTemplatePageBtn">Add selected page</button>
    <label class="inspector-control-label" for="inspectorManualBlockTemplate">Insert block on manual page</label>
    <select id="inspectorManualBlockTemplate" ${manualDisabled} aria-label="Manual block template">${manualBlockTemplateOptionsHtml('text')}</select>
    <button type="button" class="ghost full-width" id="inspectorInsertManualBlockBtn" ${manualDisabled}>Insert selected block</button>
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
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorMovePageUpBtn" ${pageDisabled}>Move page up</button>
      <button type="button" class="ghost" id="inspectorMovePageDownBtn" ${pageDisabled}>Move page down</button>
      <button type="button" class="ghost" id="inspectorDuplicatePageBtn" ${manualDisabled}>Duplicate page</button>
      <button type="button" class="ghost" id="inspectorAddManualBlockBtn" ${manualDisabled}>Add text block</button>
    </div>
    <label class="inspector-control-label" for="inspectorBlockSpacing">Selected block spacing</label>
    <select id="inspectorBlockSpacing" ${blockDisabled} aria-label="Selected block spacing">
      <option value="inherit" ${blockSpacing === 'inherit' ? 'selected' : ''}>Inherit page spacing</option>
      <option value="compact" ${blockSpacing === 'compact' ? 'selected' : ''}>Compact</option>
      <option value="standard" ${blockSpacing === 'standard' ? 'selected' : ''}>Standard</option>
      <option value="comfortable" ${blockSpacing === 'comfortable' ? 'selected' : ''}>Comfortable</option>
    </select>
    <label class="inspector-checkbox"><input type="checkbox" id="inspectorKeepBlockTogether" ${blockOverrides.keep_block_together ? 'checked' : ''} ${blockDisabled}> Keep selected block together</label>
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorMoveBlockUpBtn" ${manualBlockDisabled}>Move block up</button>
      <button type="button" class="ghost" id="inspectorMoveBlockDownBtn" ${manualBlockDisabled}>Move block down</button>
      <button type="button" class="ghost" id="inspectorDuplicateBlockBtn" ${manualBlockDisabled}>Duplicate block</button>
      <button type="button" class="danger" id="inspectorDeleteBlockBtn" ${manualBlockDisabled}>Delete block</button>
    </div>
    <p>Page ordering is stored in document_pages.sort_order. Drag the outline or use move controls; manual pages also support safe block movement and duplication.</p>
  </div>`;
}

function renderRightInspector() {
  const {fieldKey, meta, page, block} = selectedInspectorMeta();
  const pageTitle = page?.title || meta.page_title || 'No page selected';
  const pageType = pageTypeLabel(page || {page_type: meta.block_type});
  const hasBlock = !!(fieldKey || activeBlockId);
  const sourceRows = block?.source_row_ids || meta.source_row_ids || page?.source_row_ids || [];
  const fieldEntries = inspectorFieldEntriesForSelection(page, block, meta, fieldKey);
  const selectedFieldHtml = hasBlock
    ? `<div class="inspector-card selected"><div class="inspector-kicker">Selected block</div><strong>${esc(meta.field_label || block.title || 'Editable field')}</strong><dl><dt>Type</dt><dd>${esc(humanizeEditorToken(block.block_type || meta.block_type))}</dd><dt>Field</dt><dd>${esc(fieldKey || '—')}</dd><dt>Block ID</dt><dd>${esc(activeBlockId || meta.block_id || '—')}</dd></dl></div>`
    : `<div class="inspector-card empty"><strong>Select text, an image, or a page</strong><p>Click any editable block on the canvas to inspect its source, page, and text controls.</p></div>`;
  const fieldList = renderInspectorFieldList(fieldEntries, fieldKey);
  return `<aside class="right-inspector" aria-label="Selected block inspector">
    <div class="inspector-title"><strong>Inspector</strong><span>${hasBlock ? 'Block' : 'Page'}</span></div>
    <div class="inspector-card"><div class="inspector-kicker">Page</div><strong>${esc(pageTitle)}</strong><dl><dt>Type</dt><dd>${esc(pageType)}</dd><dt>Page ID</dt><dd>${esc(page?.page_id || meta.page_id || '—')}</dd></dl></div>
    ${selectedFieldHtml}
    ${renderInspectorFieldEditor(fieldKey)}
    ${renderInspectorCompareTools(fieldKey, fieldEntries)}
    ${renderInspectorTextTools(hasBlock)}
    ${renderInspectorImageTools(fieldKey)}
    ${renderInspectorLayoutTools(hasBlock, page, block)}
    <div class="inspector-card validation-card"><div class="inspector-kicker">Validation</div>${selectedPageValidationHtml(page)}</div>
    <div class="inspector-card"><div class="inspector-kicker">Editable fields</div><ul class="inspector-list field-list">${fieldList}</ul></div>
    <div class="inspector-card"><div class="inspector-kicker">Source</div><div class="source-chip-list">${renderSourceRows(sourceRows)}</div></div>
    <div class="inspector-card"><div class="inspector-kicker">Actions</div><div class="inspector-actions"><button type="button" class="ghost" id="inspectorResetFieldBtn" ${hasBlock ? '' : 'disabled'}>Reset selected field</button><button type="button" class="ghost" id="inspectorFlagIssueBtn" ${hasBlock ? '' : 'disabled'}>Flag issue</button><button type="button" class="ghost" id="inspectorClearSelectionBtn" ${hasBlock || activePageId ? '' : 'disabled'}>Clear selection</button></div></div>
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
function addManualPage(templateId = 'blank') {
  collect();
  const page = manualPageFromTemplate(templateId || 'blank');
  documentPages().push(page);
  activePageId = page.page_id;
  activeBlockId = page.manual_blocks?.[0]?.block_id || null;
  activeFieldKey = page.manual_blocks?.length ? `document_pages.${pageIndexById(page.page_id)}.manual_blocks.0.editable_fields.content_html` : `document_pages.${pageIndexById(page.page_id)}.title`;
  markDocumentPagesTouched(`${page.title || 'Manual page'} added`);
  draw();
  scrollToPage(page.page_id);
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
function moveDocumentPage(pageId, direction) {
  collect();
  const pages = sortedDocumentPages().filter(page => !page?.is_hidden);
  const currentIndex = pages.findIndex(page => page.page_id === pageId);
  if (currentIndex < 0) return;
  const current = pages[currentIndex];
  if (!documentPageCanMove(current)) return;
  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= pages.length) return;
  const target = pages[targetIndex];
  const allPages = sortedDocumentPages();
  const currentAllIndex = allPages.findIndex(page => page.page_id === pageId);
  const targetAllIndex = allPages.findIndex(page => page.page_id === target.page_id);
  if (currentAllIndex < 0 || targetAllIndex < 0) return;
  [allPages[currentAllIndex], allPages[targetAllIndex]] = [allPages[targetAllIndex], allPages[currentAllIndex]];
  renumberDocumentPageOrders(allPages);
  activePageId = pageId;
  markDocumentPagesTouched(current.page_type === 'manual' ? 'Manual page moved' : 'Page order updated');
  draw();
  scrollToPage(pageId);
}
function moveDocumentPageToIndex(pageId, targetVisibleIndex) {
  collect();
  const allPages = sortedDocumentPages();
  const moving = allPages.find(page => page.page_id === pageId);
  if (!documentPageCanMove(moving)) return;
  const visible = allPages.filter(page => !page?.is_hidden);
  const fromVisibleIndex = visible.findIndex(page => page.page_id === pageId);
  if (fromVisibleIndex < 0) return;
  const boundedTarget = Math.max(0, Math.min(Number(targetVisibleIndex || 0), visible.length - 1));
  if (boundedTarget === fromVisibleIndex) return;
  visible.splice(fromVisibleIndex, 1);
  visible.splice(boundedTarget, 0, moving);
  const hidden = allPages.filter(page => page?.is_hidden);
  renumberDocumentPageOrders([...visible, ...hidden]);
  activePageId = pageId;
  markDocumentPagesTouched('Page order updated');
  draw();
  scrollToPage(pageId);
}
function moveDocumentPageToEdge(pageId, edge) {
  const visible = sortedDocumentPages().filter(page => !page?.is_hidden);
  moveDocumentPageToIndex(pageId, edge === 'bottom' ? visible.length - 1 : 0);
}
function moveManualPage(pageId, direction) {
  moveDocumentPage(pageId, direction);
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
  const canDuplicate = page.page_type === 'manual';
  const moveControls = !isHidden ? `<button class="ghost" type="button" data-doc-page-action="move-up" data-page-id-ref="${escAttr(pageId)}">Move up</button><button class="ghost" type="button" data-doc-page-action="move-down" data-page-id-ref="${escAttr(pageId)}">Move down</button>` : '';
  const duplicateControl = canDuplicate && !isHidden ? `<button class="ghost" type="button" data-doc-page-action="duplicate" data-page-id-ref="${escAttr(pageId)}">Duplicate</button>` : '';
  const controls = `<div class="page-controls"><button class="ghost" type="button" data-outline-page-id="${escAttr(pageId)}">Select</button>${moveControls}${isHidden ? `<button class="ghost" type="button" data-doc-page-action="restore" data-page-id-ref="${escAttr(pageId)}">Restore</button>` : `<button class="danger" type="button" data-doc-page-action="hide" data-page-id-ref="${escAttr(pageId)}">Delete page</button>`}${duplicateControl}</div>`;
  if (isHidden) return '';
  return `<div class="page-wrap ${pageLayoutClasses(page)} ${activePageId === pageId ? 'selected-page' : ''}" data-page-id="${escAttr(pageId)}"><div class="page-header-row"><div class="page-label">${esc(label)}</div>${controls}</div>${bodyHtml}</div>`;
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
  const studioEdits = document.getElementById('studioEditsMetric');
  if (studioEdits) studioEdits.textContent = String(touchedKeys.size);
  const studioSelection = document.getElementById('studioSelectionMetric');
  if (studioSelection) studioSelection.textContent = activeBlockId ? 'Block selected' : (activePageId ? 'Page selected' : 'No selection');
  const readinessBadge = document.getElementById('pdfReadinessBadge');
  if (readinessBadge) {
    const status = pdfReadinessStatus();
    readinessBadge.textContent = status.label;
    readinessBadge.className = `stat-pill pdf-readiness ${status.level}`;
  }
  highlightWarnings();
}

