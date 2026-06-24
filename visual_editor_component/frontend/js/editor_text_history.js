/** Responsibility split from editor_text_tools.js. */
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
