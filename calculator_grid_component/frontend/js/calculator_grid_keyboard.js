// Dedicated Calculator frontend owner.

function handleCellKeydown(event) {
  const cell = event.currentTarget;

  if (activeCellEditing) {
    if (event.key === 'Escape') {
      event.preventDefault();
      activeCellEditing = false;
      if (cancelCellEdit()) rerender({skipCalculation: true});
      else setCellEditingMode(cell, false);
      return;
    }
    if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault();
      commitCellEdit();
      setCellEditingMode(cell, false);
      const rowDelta = event.key === 'Enter' ? (event.shiftKey ? -1 : 1) : 0;
      const colDelta = event.key === 'Tab' ? (event.shiftKey ? -1 : 1) : 0;
      moveActiveCell(cell, rowDelta, colDelta, false);
    }
    return;
  }

  if (event.key === 'F2' || event.key === 'Enter') {
    event.preventDefault();
    setCellEditingMode(cell, true, {caretAtEnd: true});
    return;
  }

  if (event.key === 'Backspace' || event.key === 'Delete') {
    event.preventDefault();
    beginCellEdit();
    updateRowValue(Number(cell.dataset.rowIndex || 0), cell.dataset.key, '');
    cell.textContent = '';
    commitCellEdit();
    markLocalDraft();
    refreshDefaultedEditableCells(Number(cell.dataset.rowIndex || 0));
    refreshFormulaCells(Number(cell.dataset.rowIndex || 0));
    refreshTotalsOnly();
    refreshValidationAndStatus();
    refreshFormulaBarOnly();
    return;
  }

  if (isPrintableCellKey(event)) {
    event.preventDefault();
    replaceSelectedCellWithTypedCharacter(cell, event.key);
    return;
  }

  const movement = navigationMovement(event);
  if (!movement) return;
  event.preventDefault();
  moveActiveCell(cell, movement.rowDelta, movement.colDelta, event.shiftKey);
}

function isPrintableCellKey(event) {
  return event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey;
}

function navigationMovement(event) {
  if (event.key === 'ArrowRight') return {rowDelta: 0, colDelta: 1};
  if (event.key === 'ArrowLeft') return {rowDelta: 0, colDelta: -1};
  if (event.key === 'ArrowDown') return {rowDelta: 1, colDelta: 0};
  if (event.key === 'ArrowUp') return {rowDelta: -1, colDelta: 0};
  if (event.key === 'Tab') return {rowDelta: 0, colDelta: event.shiftKey ? -1 : 1};
  return null;
}

function moveActiveCell(cell, rowDelta, colDelta, extendSelection = false) {
  const columns = visibleColumns(calculatorState.showAdvanced);
  const currentRowIndex = Number(cell.dataset.rowIndex || 0);
  const currentKey = cell.dataset.key;
  const currentColIndex = columns.findIndex((column) => column.key === currentKey);
  if (currentColIndex < 0) return;
  const targetRowIndex = Math.max(0, Math.min(calculatorState.rows.length - 1, currentRowIndex + rowDelta));
  const targetColIndex = Math.max(0, Math.min(columns.length - 1, currentColIndex + colDelta));
  const targetKey = columns[targetColIndex].key;
  activeCellEditing = false;
  if (extendSelection) extendCellSelection(targetRowIndex, targetKey);
  else setSingleCellSelection(targetRowIndex, targetKey);
  const target = document.querySelector(`[data-row-index="${targetRowIndex}"][data-key="${targetKey}"]`);
  if (!target) return;
  const input = target.matches('input') ? target : target.querySelector?.('input');
  if (input) {
    input.focus();
    return;
  }
  target.focus();
  clearBrowserTextSelection();
}

function replaceSelectedCellWithTypedCharacter(cell, character) {
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  setCellEditingMode(cell, true);
  setCellDisplayText(cell, character);
  placeCaretAtEnd(cell);
  const recalculated = updateRowValue(rowIndex, key, character);
  markLocalDraft(false, false);
  if (key === 'day' || key === 'from_date') refreshDateCells();
  if (recalculated) {
    refreshDefaultedEditableCells(rowIndex);
    refreshFormulaCells(calculatorUsesA1References() ? null : rowIndex);
    refreshTotalsOnly();
    refreshValidationAndStatus();
  }
  refreshFormulaBarOnly();
  if (key === 'travel_element') scheduleSuggestions(rowIndex, character);
}
