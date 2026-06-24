/** Responsibility split from editor_text_tools.js. */
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

function editableFromSelectionNode(node) {
  let candidate = node;
  if (candidate && candidate.nodeType === Node.TEXT_NODE) candidate = candidate.parentElement;
  return candidate?.closest?.('[data-edit-key]') || null;
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

function isRichEditable(el) {
  return !!(el && isHtmlEditKey(el.getAttribute('data-edit-key') || ''));
}

function richEditableContext() {
  const editable = selectedEditable();
  if (!isRichEditable(editable)) {
    notifyEditor('Select a rich day, final-page, or manual content block first.');
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
