let selectionDragging = false;

function visibleColumnIndex(key) {
  return visibleColumns(calculatorState.showAdvanced).findIndex((column) => column.key === key);
}

function setSingleCellSelection(rowIndex, key) {
  const colIndex = visibleColumnIndex(key);
  if (colIndex < 0) return;
  calculatorState.selection = {startRow: rowIndex, endRow: rowIndex, startCol: colIndex, endCol: colIndex};
}

function extendCellSelection(rowIndex, key) {
  const colIndex = visibleColumnIndex(key);
  if (colIndex < 0) return;
  const selection = calculatorState.selection || {startRow: rowIndex, endRow: rowIndex, startCol: colIndex, endCol: colIndex};
  calculatorState.selection = {...selection, endRow: rowIndex, endCol: colIndex};
  refreshSelectionClasses();
}

function normalizedSelection() {
  const selection = calculatorState.selection;
  if (!selection) return null;
  return {
    top: Math.min(selection.startRow, selection.endRow),
    bottom: Math.max(selection.startRow, selection.endRow),
    left: Math.min(selection.startCol, selection.endCol),
    right: Math.max(selection.startCol, selection.endCol)
  };
}

function cellIsSelected(rowIndex, key) {
  const selection = normalizedSelection();
  if (!selection) return false;
  const colIndex = visibleColumnIndex(key);
  return rowIndex >= selection.top && rowIndex <= selection.bottom && colIndex >= selection.left && colIndex <= selection.right;
}

function refreshSelectionClasses() {
  document.querySelectorAll('td[data-row-index][data-key]').forEach((cell) => {
    const selected = cellIsSelected(Number(cell.dataset.rowIndex), cell.dataset.key);
    cell.classList.toggle('selected-cell', selected);
  });
}

function selectedCellsAsTsv() {
  const selection = normalizedSelection();
  if (!selection) return '';
  const columns = visibleColumns(calculatorState.showAdvanced);
  const lines = [];
  for (let rowIndex = selection.top; rowIndex <= selection.bottom; rowIndex += 1) {
    const row = calculatorState.rows[rowIndex];
    const values = [];
    for (let colIndex = selection.left; colIndex <= selection.right; colIndex += 1) {
      const column = columns[colIndex];
      values.push(copyableCellValue(row, column));
    }
    lines.push(values.join('\t'));
  }
  return lines.join('\n');
}

function copyableCellValue(row, column) {
  if (!row || !column) return '';
  if (column.formula) {
    const override = row[formulaOverrideKey(column.key)];
    return override === null || override === undefined ? String(row[column.key] ?? '') : String(override);
  }
  return String(row[column.key] ?? '');
}

function applyTsvAtActiveCell(text) {
  if (!activeCell) return false;
  const matrix = String(text || '').replace(/\r/g, '').split('\n').map((line) => line.split('\t'));
  if (!matrix.length) return false;
  const columns = visibleColumns(calculatorState.showAdvanced);
  const startCol = visibleColumnIndex(activeCell.key);
  if (startCol < 0) return false;
  recordHistory();
  while (calculatorState.rows.length < activeCell.rowIndex + matrix.length) {
    calculatorState.rows = addRows(calculatorState.rows, 1);
  }
  matrix.forEach((values, rowOffset) => {
    values.forEach((value, colOffset) => {
      const column = columns[startCol + colOffset];
      if (!column) return;
      updateRowValue(activeCell.rowIndex + rowOffset, column.key, value);
    });
  });
  calculatorState.selection = {
    startRow: activeCell.rowIndex,
    endRow: activeCell.rowIndex + matrix.length - 1,
    startCol,
    endCol: Math.min(columns.length - 1, startCol + Math.max(...matrix.map((row) => row.length)) - 1)
  };
  markLocalDraft();
  rerender();
  return true;
}

function fillSelection(direction) {
  const selection = normalizedSelection();
  if (!selection) return;
  const columns = visibleColumns(calculatorState.showAdvanced);
  recordHistory();
  if (direction === 'down') {
    for (let col = selection.left; col <= selection.right; col += 1) {
      const source = copyableCellValue(calculatorState.rows[selection.top], columns[col]);
      for (let row = selection.top + 1; row <= selection.bottom; row += 1) updateRowValue(row, columns[col].key, source);
    }
  } else {
    for (let row = selection.top; row <= selection.bottom; row += 1) {
      const source = copyableCellValue(calculatorState.rows[row], columns[selection.left]);
      for (let col = selection.left + 1; col <= selection.right; col += 1) updateRowValue(row, columns[col].key, source);
    }
  }
  markLocalDraft();
  rerender();
}

function bindClipboardEvents() {
  document.oncopy = (event) => {
    const text = selectedCellsAsTsv();
    if (!text || !event.clipboardData) return;
    event.preventDefault();
    event.clipboardData.setData('text/plain', text);
  };
  document.onpaste = (event) => {
    if (!event.clipboardData || !activeCell) return;
    const text = event.clipboardData.getData('text/plain');
    if (!text.includes('\t') && !text.includes('\n')) return;
    event.preventDefault();
    applyTsvAtActiveCell(text);
  };
  document.onmouseup = () => { selectionDragging = false; };
}
