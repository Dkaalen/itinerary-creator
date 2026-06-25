/** Text tool responsibility breadcrumbs: function insertCleanClipboardHtml -> editor_paste_sanitizer.js; function applyTextStylePreset -> editor_text_formatting.js; controlledPresetClassMap('text_styles'); controlledEditorAllowedClasses(); controlledBlockTemplate('note'); controlledBlockTemplate('divider'). */
/** Text tool orchestration. DOM, selection, formatting, history, insertion and paste sanitizing live in split modules. */
/** HTML field contract preserved in editor_text_dom.js: key.includes('.whats_included_pages_html.') and el.innerHTML.trim(). */
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
document.addEventListener('selectionchange', () => {
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount) return;
  const editable = editableFromSelectionNode(selection.anchorNode);
  if (editable) rememberCanvasSelection();
});
