/** Responsibility split from editor_text_tools.js. */
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
