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
const CONTROLLED_FONT_FAMILY_CLASSES = controlledPresetClassNames('font_families');
const CONTROLLED_FONT_SIZE_CLASSES = controlledPresetClassNames('font_sizes');
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
function applyFontFamilyPreset(preset) {
  const mapping = controlledPresetClassMap('font_families');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_FONT_FAMILY_CLASSES);
}
function applyFontSizePreset(preset) {
  const mapping = controlledPresetClassMap('font_sizes');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_FONT_SIZE_CLASSES);
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
  removeClassGroup(target, CONTROLLED_FONT_FAMILY_CLASSES);
  removeClassGroup(target, CONTROLLED_FONT_SIZE_CLASSES);
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
