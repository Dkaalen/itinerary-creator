let activeCellEditing = false;
const CALCULATOR_RECALCULATION_INPUT_KEYS = new Set([
  'gross_price_per_unit',
  'units',
  'supplier_commission',
  'supplier_currency',
  'sales_price_per_unit',
  'sales_currency',
  'vat25',
  'vat15',
  'vat12',
  'vat0_domestic',
  'vat0_international',
  'gross_price',
  'net_price',
  'supplier_x_rate',
  'net_price_nok',
  'price',
  'sales_x_rate',
  'sales_price_nok_total',
  'gp_nok',
  'gp_percent'
]);

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

function handleCellInput(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  const recalculated = updateRowValue(rowIndex, key, cell.textContent || '');
  markLocalDraft(false, false);
  if (key === 'day' || key === 'from_date') refreshDateCells();
  if (recalculated) {
    refreshDefaultedEditableCells(rowIndex);
    refreshFormulaCells(calculatorUsesA1References() ? null : rowIndex);
    refreshTotalsOnly();
    refreshValidationAndStatus();
  }
  refreshFormulaBarOnly();
  if (key === 'travel_element') scheduleSuggestions(rowIndex, cell.textContent || '');
}

function handleCellKeydown(event) {
  const cell = event.currentTarget;

  if (activeCellEditing) {
    if (event.key === 'Escape') {
      event.preventDefault();
      activeCellEditing = false;
      if (cancelCellEdit()) rerender();
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

function clearBrowserTextSelection() {
  const selection = window.getSelection();
  if (selection) selection.removeAllRanges();
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

function handleCellBlur(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  if (['number', 'numberOptional', 'percent'].includes(columnKind(key))) {
    const value = row[key];
    const display = key === 'sales_price_per_unit' && value !== null && value !== undefined && value !== ''
      ? formatNumber(numberValue(value), 2)
      : (value === null || value === undefined || value === '' ? '' : String(value));
    setCellDisplayText(cell, display);
  } else if (['formula', 'formulaPercent'].includes(columnKind(key))) {
    const override = row[formulaOverrideKey(key)];
    setCellDisplayText(cell, formatFormula(row[key], columnKind(key)));
  } else if (key === 'supplier_currency' || key === 'sales_currency') {
    setCellDisplayText(cell, row[key] || '');
  }
  commitCellEdit();
  setCellEditingMode(cell, false);
  refreshSelectionClasses();
}

function handleCheckboxChange(event) {
  const checkbox = event.currentTarget;
  const rowIndex = Number(checkbox.dataset.rowIndex || 0);
  const key = checkbox.dataset.key;
  recordHistory();
  updateRowValue(rowIndex, key, Boolean(checkbox.checked));
  markLocalDraft();
}

function columnKind(key) {
  const column = columnByKey(key);
  return column?.kind || 'text';
}

function updateRowValue(rowIndex, key, rawValue, recalculate = true) {
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  const kind = columnKind(key);
  if (key === 'supplier_commission') row._supplier_commission_touched = true;
  if (key === 'supplier_currency') row.supplier_x_rate_override = null;
  if (key === 'sales_currency') row.sales_x_rate_override = null;
  if (key === 'units') row._units_touched = true;
  if (key === 'sales_price_per_unit') row._sales_price_per_unit_touched = true;
  if (key === 'day') markDayChanged(row);
  if (key === 'from_date') markDateManualState(row, key, rawValue);
  if (kind === 'checkbox') row[key] = Boolean(rawValue);
  else if (kind === 'numberOptional') row[key] = optionalNumericStorageValue(rawValue);
  else if (kind === 'formula' || kind === 'formulaPercent') row[formulaOverrideKey(key)] = formulaOverrideValue(rawValue, kind);
  else if (kind === 'percent') row[key] = rawValue === '' ? '' : percentPointInputValue(rawValue);
  else if (kind === 'number') row[key] = rawValue === '' ? '' : numericStorageValue(rawValue);
  else row[key] = normalizedTextValue(key, rawValue);
  if (key === 'day' || key === 'from_date') autofillDatesFromArrival(calculatorState.rows);
  const needsCalculation = recalculate && calculatorInputAffectsCalculations(key);
  if (needsCalculation) {
    calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  }
  return needsCalculation;
}

function calculatorInputAffectsCalculations(key) {
  return CALCULATOR_RECALCULATION_INPUT_KEYS.has(key);
}

function numericStorageValue(rawValue) {
  const parsed = parseNumericInput(rawValue);
  return parsed === null ? String(rawValue ?? '').trim() : parsed;
}

function optionalNumericStorageValue(rawValue) {
  const text = String(rawValue ?? '').trim();
  if (!text || ['none', 'nan', 'null'].includes(text.toLowerCase())) return null;
  return numericStorageValue(rawValue);
}

function normalizedTextValue(key, rawValue) {
  const text = String(rawValue ?? '');
  if (key === 'supplier_currency' || key === 'sales_currency') return text.trim().toUpperCase();
  return text;
}

function formulaOverrideValue(rawValue, kind) {
  if (rawValue === null || rawValue === undefined || String(rawValue).trim() === '') return null;
  const parsed = parseNumericInput(rawValue);
  if (parsed === null) return String(rawValue).trim();
  if (kind === 'formulaPercent') return percentInputValue(rawValue);
  return parsed;
}

function percentInputValue(rawValue) {
  const text = String(rawValue || '').trim();
  const number = numberValue(rawValue);
  return text.includes('%') ? number : number / 100;
}

function percentPointInputValue(rawValue) {
  const text = String(rawValue || '').trim();
  const parsed = parseNumericInput(rawValue);
  if (parsed === null) return text;
  return text.includes('%') ? parsed * 100 : parsed;
}

function markSelectedRow(rowIndex) {
  document.querySelectorAll('.calc-row').forEach((row) => row.classList.remove('selected-row'));
  document.querySelector(`.calc-row[data-row-index="${rowIndex}"]`)?.classList.add('selected-row');
}

function refreshDateCells() {
  for (let index = 0; index < calculatorState.rows.length; index += 1) {
    const cell = document.querySelector(`td[data-row-index="${index}"][data-key="from_date"]`);
    if (!cell || document.activeElement === cell) continue;
    setCellDisplayText(cell, calculatorState.rows[index].from_date || '');
  }
}

function refreshDefaultedEditableCells(rowIndex) {
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  for (const key of ['units', 'supplier_commission', 'sales_price_per_unit']) {
    const cell = document.querySelector(`td[data-row-index="${rowIndex}"][data-key="${key}"]`);
    if (!cell || document.activeElement === cell) continue;
    const value = row[key];
    const display = key === 'sales_price_per_unit' && value !== null && value !== undefined && value !== ''
      ? formatNumber(numberValue(value), 2)
      : (value === null || value === undefined || value === '' ? '' : String(value));
    setCellDisplayText(cell, display);
  }
}

function refreshFormulaCells(rowIndex = null) {
  const cells = rowIndex === null
    ? document.querySelectorAll('td.formula-cell[data-row-index][data-key]')
    : document.querySelectorAll(`td.formula-cell[data-row-index="${rowIndex}"][data-key]`);
  cells.forEach((cell) => {
    const currentRowIndex = Number(cell.dataset.rowIndex || 0);
    const key = cell.dataset.key;
    const row = calculatorState.rows[currentRowIndex];
    const column = columnByKey(key);
    if (!row || !column) return;
    if (activeCell && activeCell.rowIndex === currentRowIndex && activeCell.key === key && document.activeElement === cell) return;
    setCellDisplayText(cell, formatFormula(row[key], column.kind));
  });
}

function calculatorUsesA1References() {
  return calculatorState.rows.some((row) => Object.entries(row).some(([key, value]) => {
    if (key.startsWith('_') || typeof value !== 'string' || !value.trim().startsWith('=')) return false;
    return /\$?[A-Za-z]{1,2}\$?\d+/.test(value);
  }));
}

function activeCellRawValue() {
  if (!activeCell) return '';
  const row = calculatorState.rows[activeCell.rowIndex];
  const column = columnByKey(activeCell.key);
  if (!row || !column) return '';
  if (column.formula) {
    const override = row[formulaOverrideKey(column.key)];
    return override === null || override === undefined ? formatFormula(row[column.key], column.kind) : String(override);
  }
  if (column.key === 'sales_price_per_unit') {
    const value = row[column.key];
    if (value === null || value === undefined || value === '') return '';
    const parsed = parseNumericInput(value);
    return parsed === null ? String(value) : formatNumber(parsed, 2);
  }
  return String(row[column.key] ?? '');
}

function updateActiveCellFromFormulaBar(value) {
  if (!activeCell) return;
  const recalculated = updateRowValue(activeCell.rowIndex, activeCell.key, value);
  markLocalDraft(false, false);
  refreshActiveCellDisplayFromState();
  if (recalculated) {
    refreshDefaultedEditableCells(activeCell.rowIndex);
    refreshFormulaCells(calculatorUsesA1References() ? null : activeCell.rowIndex);
    refreshTotalsOnly();
    refreshValidationAndStatus();
  }
}

function refreshActiveCellDisplayFromState() {
  if (!activeCell) return;
  const row = calculatorState.rows[activeCell.rowIndex];
  const column = columnByKey(activeCell.key);
  const cell = document.querySelector(`td[data-row-index="${activeCell.rowIndex}"][data-key="${activeCell.key}"]`);
  if (!row || !column || !cell) return;
  const display = column.formula
    ? formatFormula(row[column.key], column.kind)
    : editableCellDisplayValue(row, column);
  setCellDisplayText(cell, display);
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
