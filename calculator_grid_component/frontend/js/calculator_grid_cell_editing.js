// Cell mouse/focus editing lifecycle.

function handleCellMouseDown(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  const wasActive = sameActiveCell(rowIndex, key);
  selectionDragging = true;
  if (event.shiftKey && calculatorState.selection) extendCellSelection(rowIndex, key);
  else setSingleCellSelection(rowIndex, key);
  refreshSelectionClasses();

  if (!wasActive) {
    event.preventDefault();
    activeCell = {rowIndex, key};
    calculatorState.selectedRowIndex = rowIndex;
    setCellEditingMode(cell, false);
    cell.focus({preventScroll: true});
    clearBrowserTextSelection();
    markSelectedRow(rowIndex);
    refreshFormulaBarOnly();
    return;
  }

  if (!activeCellEditing) setCellEditingMode(cell, true);
}

function handleCellMouseEnter(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  if (fillDragSource) {
    updateFillDrag(rowIndex, cell.dataset.key);
    return;
  }
  if (!selectionDragging || !(event.buttons & 1)) return;
  extendCellSelection(rowIndex, cell.dataset.key);
}

function handleCellFocus(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  calculatorState.selectedRowIndex = rowIndex;
  activeCell = {rowIndex, key};
  if (!calculatorState.selection) setSingleCellSelection(rowIndex, key);
  if (key === 'travel_element' && activeCellEditing) scheduleSuggestions(rowIndex, cell.textContent || '');
  markSelectedRow(rowIndex);
  refreshFormulaBarOnly();
}
