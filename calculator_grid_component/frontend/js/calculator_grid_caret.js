// Dedicated Calculator frontend owner.

let activeCellEditing = false;

function sameActiveCell(rowIndex, key) {
  return Boolean(activeCell && activeCell.rowIndex === rowIndex && activeCell.key === key);
}

function setCellEditingMode(cell, editing, {caretAtEnd = false} = {}) {
  activeCellEditing = Boolean(editing);
  document.querySelectorAll('td.editing-cell').forEach((item) => item.classList.remove('editing-cell'));
  if (!cell || !activeCellEditing) return;
  cell.classList.add('editing-cell');
  cell.querySelector(':scope > .fill-handle')?.remove();
  beginCellEdit();
  if (caretAtEnd) placeCaretAtEnd(cell);
}

function clearBrowserTextSelection() {
  const selection = window.getSelection();
  if (selection) selection.removeAllRanges();
}

function setCellDisplayText(cell, value) {
  if (!cell) return;
  const handle = cell.querySelector(':scope > .fill-handle');
  if (handle) handle.remove();
  cell.textContent = String(value ?? '');
  if (handle && !cell.classList.contains('editing-cell')) cell.appendChild(handle);
}

function placeCaretAtEnd(cell) {
  const range = document.createRange();
  range.selectNodeContents(cell);
  range.collapse(false);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

function restoreActiveCellFocus() {
  refreshSelectionClasses();
  if (!activeCell) return;
  const target = document.querySelector(`[data-row-index="${activeCell.rowIndex}"][data-key="${activeCell.key}"]`);
  if (!target || target.matches('input')) return;
  activeCellEditing = false;
  target.focus({preventScroll: true});
  clearBrowserTextSelection();
}
