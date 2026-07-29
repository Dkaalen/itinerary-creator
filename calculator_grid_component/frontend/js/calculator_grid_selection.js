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
  refreshFillHandle();
}

function refreshFillHandle() {
  document.querySelectorAll('.fill-handle').forEach((handle) => handle.remove());
  const selection = normalizedSelection();
  if (!selection) return;
  const columns = visibleColumns(calculatorState.showAdvanced);
  const key = columns[selection.right]?.key;
  if (!key) return;
  const cell = document.querySelector(`td[data-row-index="${selection.bottom}"][data-key="${key}"]`);
  if (!cell) return;
  const handle = document.createElement('span');
  handle.className = 'fill-handle';
  handle.contentEditable = 'false';
  handle.setAttribute('aria-hidden', 'true');
  handle.addEventListener('mousedown', startFillDrag);
  cell.appendChild(handle);
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


function translatedCellValue(value, sourceRowIndex, sourceColumn, targetRowIndex, targetColumn) {
  const sourceColumnIndex = CALCULATOR_COLUMNS.findIndex((column) => column.key === sourceColumn?.key);
  const targetColumnIndex = CALCULATOR_COLUMNS.findIndex((column) => column.key === targetColumn?.key);
  return translateFormulaReferences(
    value,
    Number(targetRowIndex) - Number(sourceRowIndex),
    targetColumnIndex - sourceColumnIndex
  );
}

const CALCULATOR_CLIPBOARD_MIME = 'application/x-itinerary-calculator-grid+json';
let calculatorClipboardMemory = null;
window.addEventListener('blur', () => { calculatorClipboardMemory = null; });

function clipboardMatrix(text) {
  let normalized = String(text ?? '').replace(/\r\n?/g, '\n');
  if (normalized.endsWith('\n')) normalized = normalized.slice(0, -1);
  const rows = normalized.split('\n').map((line) => line.split('\t'));
  const width = Math.max(1, ...rows.map((row) => row.length));
  return rows.map((row) => [...row, ...Array(width - row.length).fill('')]);
}

function selectedCellsAsClipboardPayload() {
  const selection = normalizedSelection();
  if (!selection) return null;
  const columns = visibleColumns(calculatorState.showAdvanced);
  const cells = [];
  for (let rowIndex = selection.top; rowIndex <= selection.bottom; rowIndex += 1) {
    const row = calculatorState.rows[rowIndex];
    const values = [];
    for (let colIndex = selection.left; colIndex <= selection.right; colIndex += 1) {
      const column = columns[colIndex];
      values.push({
        value: copyableCellValue(row, column),
        sourceRowIndex: rowIndex,
        sourceColumnKey: column?.key || ''
      });
    }
    cells.push(values);
  }
  return {version: 1, cells};
}

function calculatorClipboardPayloadIsValid(payload) {
  if (payload?.version !== 1 || !Array.isArray(payload.cells) || !payload.cells.length) return false;
  if (payload.cells.length > MAX_CALCULATOR_ROWS) return false;
  return payload.cells.every((row) => Array.isArray(row)
    && row.length > 0
    && row.length <= CALCULATOR_COLUMNS.length
    && row.every((cell) => cell
      && Number.isInteger(Number(cell.sourceRowIndex))
      && Number(cell.sourceRowIndex) >= 0
      && Number(cell.sourceRowIndex) < MAX_CALCULATOR_ROWS
      && Boolean(columnByKey(cell.sourceColumnKey))));
}

function parseCalculatorClipboardPayload(dataTransfer) {
  if (!dataTransfer) return null;
  try {
    const raw = dataTransfer.getData(CALCULATOR_CLIPBOARD_MIME);
    if (!raw) return null;
    const payload = JSON.parse(raw);
    return calculatorClipboardPayloadIsValid(payload) ? payload : null;
  } catch (_error) {
    return null;
  }
}

function calculatorClipboardPayloadForPaste(dataTransfer, text) {
  const embedded = parseCalculatorClipboardPayload(dataTransfer);
  if (embedded) return embedded;
  if (!calculatorClipboardMemory || calculatorClipboardMemory.text !== text) return null;
  if (Date.now() - calculatorClipboardMemory.copiedAt > 120000) return null;
  return calculatorClipboardMemory.payload;
}

function clipboardTargetPlan(matrix) {
  if (!activeCell || !matrix.length) return null;
  const columns = visibleColumns(calculatorState.showAdvanced);
  const activeCol = visibleColumnIndex(activeCell.key);
  if (activeCol < 0) return null;
  const selection = normalizedSelection();
  const matrixRows = matrix.length;
  const matrixCols = Math.max(1, ...matrix.map((row) => row.length));
  const hasRange = Boolean(selection && (selection.bottom > selection.top || selection.right > selection.left));
  if (hasRange) {
    const selectedRows = selection.bottom - selection.top + 1;
    const selectedCols = selection.right - selection.left + 1;
    const tileSelection = (matrixRows === 1 && matrixCols === 1)
      || (selectedRows % matrixRows === 0 && selectedCols % matrixCols === 0);
    if (tileSelection) return {...selection, tile: true, columns};
    return {
      top: selection.top,
      bottom: Math.min(MAX_CALCULATOR_ROWS - 1, selection.top + matrixRows - 1),
      left: selection.left,
      right: Math.min(columns.length - 1, selection.left + matrixCols - 1),
      tile: false,
      columns
    };
  }
  const top = selection?.top ?? activeCell.rowIndex;
  const left = selection?.left ?? activeCol;
  return {
    top,
    bottom: Math.min(MAX_CALCULATOR_ROWS - 1, top + matrixRows - 1),
    left,
    right: Math.min(columns.length - 1, left + matrixCols - 1),
    tile: false,
    columns
  };
}

function clipboardValueForTarget(value, internalCell, targetRowIndex, targetColumn) {
  if (!internalCell) return value;
  const sourceColumn = columnByKey(internalCell.sourceColumnKey);
  if (!sourceColumn) return value;
  return translatedCellValue(
    internalCell.value,
    Number(internalCell.sourceRowIndex),
    sourceColumn,
    targetRowIndex,
    targetColumn
  );
}

function normalizedClipboardValue(column, value) {
  if (column?.kind !== 'checkbox') return value;
  if (typeof value === 'boolean') return value;
  return ['true', '1', 'yes', 'y', 'x'].includes(String(value ?? '').trim().toLowerCase());
}

function applyClipboardToGrid(text, internalPayload = null) {
  const matrix = internalPayload?.cells?.length
    ? internalPayload.cells.map((row) => row.map((cell) => String(cell?.value ?? '')))
    : clipboardMatrix(text);
  const plan = clipboardTargetPlan(matrix);
  if (!plan) return false;
  recordHistory();
  let dateAutofillNeeded = false;
  while (calculatorState.rows.length <= plan.bottom && calculatorState.rows.length < MAX_CALCULATOR_ROWS) {
    calculatorState.rows = addRows(calculatorState.rows, 1);
  }
  for (let rowIndex = plan.top; rowIndex <= plan.bottom; rowIndex += 1) {
    const sourceRowOffset = plan.tile ? (rowIndex - plan.top) % matrix.length : rowIndex - plan.top;
    const sourceValues = matrix[sourceRowOffset] || [];
    const internalValues = internalPayload?.cells?.[sourceRowOffset] || [];
    for (let colIndex = plan.left; colIndex <= plan.right; colIndex += 1) {
      const sourceColOffset = plan.tile
        ? (colIndex - plan.left) % Math.max(1, sourceValues.length)
        : colIndex - plan.left;
      if (sourceColOffset >= sourceValues.length) continue;
      const column = plan.columns[colIndex];
      if (!column) continue;
      const internalCell = internalValues[sourceColOffset] || null;
      const translated = clipboardValueForTarget(sourceValues[sourceColOffset], internalCell, rowIndex, column);
      if (column.key === 'day' || column.key === 'from_date') dateAutofillNeeded = true;
      updateRowValue(rowIndex, column.key, normalizedClipboardValue(column, translated), false, {deferDateAutofill: true});
    }
  }
  if (dateAutofillNeeded) {
    applyDeferredTripStartDate(calculatorState);
    autofillDatesFromArrival(calculatorState.rows, calculatorState.tripStartDate);
  }
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  validateCalculatorState(calculatorState);
  calculatorState.selection = {
    startRow: plan.top,
    endRow: plan.bottom,
    startCol: plan.left,
    endCol: plan.right
  };
  calculatorState.selectedRowIndex = plan.top;
  activeCell = {rowIndex: plan.top, key: plan.columns[plan.left].key};
  markLocalDraft();
  rerender({skipCalculation: true});
  return true;
}

function applyTsvAtActiveCell(text) {
  return applyClipboardToGrid(text, null);
}

function parseTextNumberSeries(value) {
  const match = String(value ?? '').match(/^(.*?)(-?\d+)(\D*)$/);
  if (!match) return null;
  return {
    prefix: match[1],
    number: Number(match[2]),
    suffix: match[3],
    width: match[2].replace('-', '').length
  };
}

function inferTextNumberSeries(values) {
  const parsed = values.map(parseTextNumberSeries);
  if (!parsed.length || parsed.some((item) => !item)) return null;
  const first = parsed[0];
  if (parsed.some((item) => item.prefix !== first.prefix || item.suffix !== first.suffix)) return null;
  const step = parsed.length === 1 ? 1 : parsed[1].number - parsed[0].number;
  if (parsed.some((item, index) => index > 0 && item.number - parsed[index - 1].number !== step)) return null;
  return {...first, step};
}

function formatTextNumberSeries(series, offset) {
  const number = series.number + series.step * offset;
  const sign = number < 0 ? '-' : '';
  const digits = String(Math.abs(number)).padStart(series.width, '0');
  return `${series.prefix}${sign}${digits}${series.suffix}`;
}

function fillSelection(direction) {
  const selection = normalizedSelection();
  if (!selection) return false;
  const columns = visibleColumns(calculatorState.showAdvanced);
  let seriesPlans = null;
  if (direction === 'seriesDown') {
    seriesPlans = [];
    for (let col = selection.left; col <= selection.right; col += 1) {
      const column = columns[col];
      const values = [];
      for (let row = selection.top; row <= selection.bottom; row += 1) {
        const value = copyableCellValue(calculatorState.rows[row], column);
        if (String(value).trim() === '') break;
        values.push(value);
      }
      const series = inferTextNumberSeries(values);
      if (!series || values.length >= selection.bottom - selection.top + 1) continue;
      seriesPlans.push({column, series, sourceCount: Math.max(1, values.length)});
    }
    if (!seriesPlans.length) {
      calculatorState.syncStatus = 'Select a range beginning with a numbered value such as Day 1.';
      refreshSyncStatusOnly();
      return false;
    }
  }
  recordHistory();
  let dateAutofillNeeded = false;
  if (direction === 'seriesDown') {
    for (const plan of seriesPlans) {
      for (let row = selection.top + plan.sourceCount; row <= selection.bottom; row += 1) {
        if (plan.column.key === 'day' || plan.column.key === 'from_date') dateAutofillNeeded = true;
        updateRowValue(row, plan.column.key, formatTextNumberSeries(plan.series, row - selection.top), false, {deferDateAutofill: true});
      }
    }
  } else if (direction === 'down') {
    for (let col = selection.left; col <= selection.right; col += 1) {
      const sourceColumn = columns[col];
      const source = copyableCellValue(calculatorState.rows[selection.top], sourceColumn);
      for (let row = selection.top + 1; row <= selection.bottom; row += 1) {
        if (sourceColumn.key === 'day' || sourceColumn.key === 'from_date') dateAutofillNeeded = true;
        updateRowValue(row, sourceColumn.key, translatedCellValue(source, selection.top, sourceColumn, row, sourceColumn), false, {deferDateAutofill: true});
      }
    }
  } else {
    for (let row = selection.top; row <= selection.bottom; row += 1) {
      const sourceColumn = columns[selection.left];
      const source = copyableCellValue(calculatorState.rows[row], sourceColumn);
      for (let col = selection.left + 1; col <= selection.right; col += 1) {
        const targetColumn = columns[col];
        if (targetColumn.key === 'day' || targetColumn.key === 'from_date') dateAutofillNeeded = true;
        updateRowValue(row, targetColumn.key, translatedCellValue(source, row, sourceColumn, row, targetColumn), false, {deferDateAutofill: true});
      }
    }
  }
  if (dateAutofillNeeded) {
    applyDeferredTripStartDate(calculatorState);
    autofillDatesFromArrival(calculatorState.rows, calculatorState.tripStartDate);
  }
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  validateCalculatorState(calculatorState);
  markLocalDraft();
  rerender({skipCalculation: true});
  return true;
}

function clipboardTargetIsNativeTextField(target) {
  return Boolean(target && (target.matches?.('input, textarea') || target.isContentEditable && !target.matches?.('td.editable')));
}

function insertPlainTextAtCaret(cell, text) {
  if (!cell) return false;
  const selection = window.getSelection();
  const normalized = String(text ?? '').replace(/\r/g, '');
  if (!selection || !selection.rangeCount || !cell.contains(selection.anchorNode)) {
    setCellDisplayText(cell, `${cell.textContent || ''}${normalized}`);
    placeCaretAtEnd(cell);
    return true;
  }
  const range = selection.getRangeAt(0);
  range.deleteContents();
  const node = document.createTextNode(normalized);
  range.insertNode(node);
  range.setStartAfter(node);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
  return true;
}

function bindClipboardEvents() {
  document.oncopy = (event) => {
    calculatorClipboardMemory = null;
    if (clipboardTargetIsNativeTextField(event.target) || activeCellEditing) return;
    const selection = normalizedSelection();
    if (!selection || !event.clipboardData) return;
    const text = selectedCellsAsTsv();
    const payload = selectedCellsAsClipboardPayload();
    calculatorClipboardMemory = payload ? {text, payload, copiedAt: Date.now()} : null;
    event.preventDefault();
    event.clipboardData.setData('text/plain', text);
    if (payload) {
      try {
        event.clipboardData.setData(CALCULATOR_CLIPBOARD_MIME, JSON.stringify(payload));
      } catch (_error) {
        // Plain TSV remains the cross-application clipboard contract.
      }
    }
  };
  document.onpaste = (event) => {
    if (!event.clipboardData || !activeCell || clipboardTargetIsNativeTextField(event.target)) return;
    const text = event.clipboardData.getData('text/plain');
    const editingCell = activeCellEditing ? event.target?.closest?.('td.editable') : null;
    event.preventDefault();
    if (editingCell) {
      insertPlainTextAtCaret(editingCell, text);
      handleCellInput({currentTarget: editingCell});
      return;
    }
    applyClipboardToGrid(text, calculatorClipboardPayloadForPaste(event.clipboardData, text));
  };
  document.onmouseup = () => { selectionDragging = false; };
}
