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
  return key && (key.endsWith('.blocks_html') || key.endsWith('.whats_included_html') || key.endsWith('.whats_not_included_html') || key.includes('.whats_included_pages_html.'));
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
const CONTROLLED_TEXT_STYLE_CLASSES = [
  've-text-small-note',
  've-text-large',
  've-text-heading',
  've-text-subheading',
  've-text-muted',
  've-text-accent',
];
const CONTROLLED_COLOR_CLASSES = [
  've-color-muted',
  've-color-accent',
  've-color-warning',
  've-color-highlight',
];
const CONTROLLED_SPACING_CLASSES = [
  've-spacing-compact',
  've-spacing-normal',
];

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
  const mapping = {
    normal: '',
    small_note: 've-text-small-note',
    large_text: 've-text-large',
    heading: 've-text-heading',
    subheading: 've-text-subheading',
    muted_text: 've-text-muted',
    accent_text: 've-text-accent',
  };
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_TEXT_STYLE_CLASSES);
}
function applyColorPreset(preset) {
  const mapping = {
    default: '',
    muted_grey: 've-color-muted',
    accent_gold: 've-color-accent',
    warning: 've-color-warning',
    soft_highlight: 've-color-highlight',
  };
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_COLOR_CLASSES);
}
function applySpacingPreset(preset) {
  const mapping = {compact: 've-spacing-compact', normal: 've-spacing-normal'};
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
  insertControlledBlock('<div class="content-block ve-note-block"><div class="body-text ve-text-small-note ve-color-muted">Note: Add your note here.</div></div>');
}
function addDividerBlock() {
  insertControlledBlock('<div class="content-block ve-divider-block"><div class="ve-divider">&nbsp;</div></div>');
}
function makeSelectedBlockClass(className) {
  const mapping = {'section-title': 'heading', '': 'normal'};
  applyTextStylePreset(mapping[className] || 'normal');
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
    'inclusion-multiline-list','ve-text-small-note','ve-text-large','ve-text-heading',
    've-text-subheading','ve-text-muted','ve-text-accent','ve-color-muted','ve-color-accent',
    've-color-warning','ve-color-highlight','ve-spacing-compact','ve-spacing-normal',
    've-note-block','ve-divider-block','ve-divider'
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
function currentListItem() {
  const selection = window.getSelection();
  let node = selection?.anchorNode || document.activeElement;
  if (node && node.nodeType === Node.TEXT_NODE) node = node.parentElement;
  return node?.closest?.('li') || null;
}
function editableForListAction() {
  const li = currentListItem();
  if (li) return li.closest('[data-edit-key]');
  return selectedEditable();
}
function addBullet() {
  const el = editableForListAction();
  if (!el) return;
  pushUndo(el, editableValue(el));
  let list = currentListItem()?.parentElement || el.querySelector('ul,ol');
  if (!list) {
    el.insertAdjacentHTML('beforeend', '<ul><li>New item</li></ul>');
  } else {
    const li = currentListItem();
    const newLi = document.createElement('li');
    newLi.textContent = 'New item';
    if (li && li.parentElement === list) li.insertAdjacentElement('afterend', newLi);
    else list.appendChild(newLi);
  }
  markTouched(el.getAttribute('data-edit-key'));
  requestAnimationFrame(adjustDayImages);
}
function deleteBullet() {
  const li = currentListItem();
  const el = li?.closest?.('[data-edit-key]');
  if (!li || !el) return;
  pushUndo(el, editableValue(el));
  li.remove();
  markTouched(el.getAttribute('data-edit-key'));
  requestAnimationFrame(adjustDayImages);
}
function moveBullet(direction) {
  const li = currentListItem();
  const el = li?.closest?.('[data-edit-key]');
  if (!li || !el) return;
  pushUndo(el, editableValue(el));
  if (direction < 0 && li.previousElementSibling) li.parentElement.insertBefore(li, li.previousElementSibling);
  if (direction > 0 && li.nextElementSibling) li.parentElement.insertBefore(li.nextElementSibling, li);
  markTouched(el.getAttribute('data-edit-key'));
  requestAnimationFrame(adjustDayImages);
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

