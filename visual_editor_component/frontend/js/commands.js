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
  activePageId = pageId;
  requestAnimationFrame(() => {
    const target = document.querySelector(`[data-page-id="${CSS.escape(pageId)}"]`);
    if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
    document.querySelectorAll('[data-page-id]').forEach(el => el.classList.toggle('selected-page', el.getAttribute('data-page-id') === pageId));
    document.querySelectorAll('[data-outline-page-id]').forEach(el => el.classList.toggle('active', el.getAttribute('data-outline-page-id') === pageId));
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

