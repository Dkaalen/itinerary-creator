let fillDragSource = null;
let fillDragTarget = null;
let columnResizeState = null;

function selectedRowBounds() {
  const selection = normalizedSelection();
  if (!selection) {
    const rowIndex = Math.max(0, Number(calculatorState.selectedRowIndex || 0));
    return {top: rowIndex, bottom: rowIndex};
  }
  return {top: selection.top, bottom: selection.bottom};
}

function insertRowsAtSelection(position) {
  commitCellEdit();
  const bounds = selectedRowBounds();
  const count = Math.max(1, bounds.bottom - bounds.top + 1);
  const insertAt = position === 'below' ? bounds.bottom + 1 : bounds.top;
  recordHistory();
  const additions = [];
  let working = [...calculatorState.rows];
  for (let index = 0; index < count; index += 1) {
    const row = createBlankRow(nextRowId([...working, ...additions]));
    additions.push(row);
  }
  working.splice(insertAt, 0, ...additions);
  calculatorState.rows = calculateRows(working, calculatorState.currencyRates);
  calculatorState.selectedRowIndex = insertAt;
  activeCell = {rowIndex: insertAt, key: visibleColumns(calculatorState.showAdvanced)[0].key};
  setSingleCellSelection(insertAt, activeCell.key);
  markLocalDraft();
  rerender();
}

function duplicateSelectedRows() {
  commitCellEdit();
  const bounds = selectedRowBounds();
  const sourceRows = calculatorState.rows.slice(bounds.top, bounds.bottom + 1);
  if (!sourceRows.length) return;
  recordHistory();
  const copies = [];
  let working = [...calculatorState.rows];
  for (const source of sourceRows) {
    const copy = {...source, row_id: nextRowId([...working, ...copies])};
    copies.push(copy);
  }
  working.splice(bounds.bottom + 1, 0, ...copies);
  calculatorState.rows = calculateRows(working, calculatorState.currencyRates);
  const columns = visibleColumns(calculatorState.showAdvanced);
  calculatorState.selection = {
    startRow: bounds.bottom + 1,
    endRow: bounds.bottom + copies.length,
    startCol: 0,
    endCol: columns.length - 1
  };
  calculatorState.selectedRowIndex = bounds.bottom + 1;
  activeCell = {rowIndex: bounds.bottom + 1, key: columns[0].key};
  markLocalDraft();
  rerender();
}

function deleteSelectedRows() {
  commitCellEdit();
  const bounds = selectedRowBounds();
  if (calculatorState.rows.length <= 1) return;
  recordHistory();
  const keep = calculatorState.rows.filter((_, index) => index < bounds.top || index > bounds.bottom);
  calculatorState.rows = calculateRows(keep.length ? keep : [createBlankRow('1')], calculatorState.currencyRates);
  const targetRow = Math.min(bounds.top, calculatorState.rows.length - 1);
  const firstKey = visibleColumns(calculatorState.showAdvanced)[0].key;
  calculatorState.selectedRowIndex = targetRow;
  activeCell = {rowIndex: targetRow, key: firstKey};
  setSingleCellSelection(targetRow, firstKey);
  markLocalDraft();
  rerender();
}

function cellIsFillHandleCorner(rowIndex, key) {
  const selection = normalizedSelection();
  if (!selection) return false;
  return rowIndex === selection.bottom && visibleColumnIndex(key) === selection.right;
}

function startFillDrag(event) {
  event.preventDefault();
  event.stopPropagation();
  fillDragSource = normalizedSelection();
  fillDragTarget = fillDragSource ? {...fillDragSource} : null;
  selectionDragging = false;
  document.body.classList.add('calculator-fill-dragging');
}

function updateFillDrag(rowIndex, key) {
  if (!fillDragSource) return false;
  const colIndex = visibleColumnIndex(key);
  if (colIndex < 0) return true;
  fillDragTarget = {
    top: Math.min(fillDragSource.top, rowIndex),
    bottom: Math.max(fillDragSource.bottom, rowIndex),
    left: Math.min(fillDragSource.left, colIndex),
    right: Math.max(fillDragSource.right, colIndex)
  };
  calculatorState.selection = {
    startRow: fillDragTarget.top,
    endRow: fillDragTarget.bottom,
    startCol: fillDragTarget.left,
    endCol: fillDragTarget.right
  };
  refreshSelectionClasses();
  return true;
}

function finishFillDrag() {
  if (!fillDragSource || !fillDragTarget) return;
  const source = fillDragSource;
  const target = fillDragTarget;
  fillDragSource = null;
  fillDragTarget = null;
  document.body.classList.remove('calculator-fill-dragging');
  if (source.top === target.top && source.bottom === target.bottom && source.left === target.left && source.right === target.right) return;
  const columns = visibleColumns(calculatorState.showAdvanced);
  const sourceValues = [];
  for (let row = source.top; row <= source.bottom; row += 1) {
    const values = [];
    for (let col = source.left; col <= source.right; col += 1) values.push(copyableCellValue(calculatorState.rows[row], columns[col]));
    sourceValues.push(values);
  }
  recordHistory();
  for (let row = target.top; row <= target.bottom; row += 1) {
    for (let col = target.left; col <= target.right; col += 1) {
      if (row >= source.top && row <= source.bottom && col >= source.left && col <= source.right) continue;
      const value = sourceValues[(row - target.top) % sourceValues.length][(col - target.left) % sourceValues[0].length];
      updateRowValue(row, columns[col].key, value);
    }
  }
  markLocalDraft();
  rerender();
}

function beginColumnResize(event) {
  event.preventDefault();
  event.stopPropagation();
  const key = event.currentTarget.dataset.columnKey;
  const column = columnByKey(key);
  if (!column) return;
  const th = event.currentTarget.closest('th');
  recordHistory();
  columnResizeState = {
    key,
    startX: event.clientX,
    startWidth: th ? th.getBoundingClientRect().width : dynamicColumnWidth(column, calculatorState.rows)
  };
  document.body.classList.add('calculator-column-resizing');
}

function updateColumnResize(event) {
  if (!columnResizeState) return;
  const column = columnByKey(columnResizeState.key);
  if (!column) return;
  const minimum = Math.max(44, Number(column.minWidth || 44));
  const maximum = Math.max(minimum, Number(column.resizeMaxWidth || 720));
  const width = Math.round(Math.max(minimum, Math.min(maximum, columnResizeState.startWidth + event.clientX - columnResizeState.startX)));
  calculatorState.columnWidths[columnResizeState.key] = width;
  if (columnResizeState.key === 'row_id') document.querySelector('.calculator-grid-shell')?.style.setProperty('--sticky-col-1-left', `${width}px`);
  document.querySelectorAll(`[data-column-key="${columnResizeState.key}"], td[data-key="${columnResizeState.key}"]`).forEach((element) => {
    element.style.width = `${width}px`;
    element.style.minWidth = `${width}px`;
    element.style.maxWidth = `${width}px`;
  });
}

function finishColumnResize() {
  if (!columnResizeState) return;
  columnResizeState = null;
  document.body.classList.remove('calculator-column-resizing');
  markLocalDraft();
  rerender();
}

function toggleFindReplace(forceOpen = null) {
  calculatorState.showFindReplace = forceOpen === null ? !calculatorState.showFindReplace : Boolean(forceOpen);
  rerender();
  if (calculatorState.showFindReplace) requestAnimationFrame(() => document.querySelector('[data-action="find-query"]')?.focus());
}

function searchableCellEntries() {
  const entries = [];
  const columns = CALCULATOR_COLUMNS.filter((column) => column.kind !== 'checkbox');
  calculatorState.rows.forEach((row, rowIndex) => {
    columns.forEach((column) => {
      const value = copyableCellValue(row, column);
      entries.push({rowIndex, key: column.key, value: String(value ?? '')});
    });
  });
  return entries;
}

function findNextCalculatorMatch() {
  const query = String(calculatorState.findQuery || '');
  if (!query) return false;
  const entries = searchableCellEntries();
  const start = Math.max(-1, Number(calculatorState.findMatchCursor ?? -1));
  for (let offset = 1; offset <= entries.length; offset += 1) {
    const index = (start + offset) % entries.length;
    if (!entries[index].value.toLowerCase().includes(query.toLowerCase())) continue;
    calculatorState.findMatchCursor = index;
    revealCalculatorMatch(entries[index]);
    return true;
  }
  calculatorState.syncStatus = `No matches for “${query}”`;
  refreshSyncStatusOnly();
  return false;
}

function revealCalculatorMatch(match) {
  if (!match) return;
  const column = columnByKey(match.key);
  if (column?.advanced && !calculatorState.showAdvanced) calculatorState.showAdvanced = true;
  calculatorState.selectedRowIndex = match.rowIndex;
  activeCell = {rowIndex: match.rowIndex, key: match.key};
  setSingleCellSelection(match.rowIndex, match.key);
  rerender();
  document.querySelector(`[data-row-index="${match.rowIndex}"][data-key="${match.key}"]`)?.scrollIntoView({block: 'nearest', inline: 'nearest'});
}

function replaceCurrentCalculatorMatch() {
  const entries = searchableCellEntries();
  const match = entries[Number(calculatorState.findMatchCursor ?? -1)];
  const query = String(calculatorState.findQuery || '');
  if (!match || !query || !match.value.toLowerCase().includes(query.toLowerCase())) {
    findNextCalculatorMatch();
    return;
  }
  recordHistory();
  const replaced = replaceTextInsensitive(match.value, query, String(calculatorState.replaceQuery || ''), false);
  updateRowValue(match.rowIndex, match.key, replaced);
  markLocalDraft();
  findNextCalculatorMatch();
}

function replaceAllCalculatorMatches() {
  const query = String(calculatorState.findQuery || '');
  if (!query) return;
  const entries = searchableCellEntries().filter((entry) => entry.value.toLowerCase().includes(query.toLowerCase()));
  if (!entries.length) {
    calculatorState.syncStatus = `No matches for “${query}”`;
    refreshSyncStatusOnly();
    return;
  }
  recordHistory();
  for (const entry of entries) {
    updateRowValue(entry.rowIndex, entry.key, replaceTextInsensitive(entry.value, query, String(calculatorState.replaceQuery || ''), true));
  }
  calculatorState.findMatchCursor = -1;
  markLocalDraft();
  rerender();
}

function replaceTextInsensitive(value, query, replacement, replaceAll) {
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return String(value).replace(new RegExp(escaped, replaceAll ? 'gi' : 'i'), replacement);
}

function bindAdvancedCalculatorEvents() {
  document.querySelectorAll('.column-resize-handle').forEach((handle) => handle.addEventListener('mousedown', beginColumnResize));
  document.querySelectorAll('.fill-handle').forEach((handle) => handle.addEventListener('mousedown', startFillDrag));
  document.querySelector('[data-action="find-query"]')?.addEventListener('input', (event) => {
    calculatorState.findQuery = event.target.value;
    calculatorState.findMatchCursor = -1;
  });
  document.querySelector('[data-action="replace-query"]')?.addEventListener('input', (event) => { calculatorState.replaceQuery = event.target.value; });
  document.querySelector('[data-action="find-next"]')?.addEventListener('click', findNextCalculatorMatch);
  document.querySelector('[data-action="replace-current"]')?.addEventListener('click', replaceCurrentCalculatorMatch);
  document.querySelector('[data-action="replace-all"]')?.addEventListener('click', replaceAllCalculatorMatches);
  document.querySelector('[data-action="close-find"]')?.addEventListener('click', () => toggleFindReplace(false));
}

document.addEventListener('mousemove', updateColumnResize);
document.addEventListener('mouseup', () => {
  finishColumnResize();
  finishFillDrag();
});
