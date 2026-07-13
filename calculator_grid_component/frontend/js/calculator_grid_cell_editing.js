function handleCellMouseDown(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  selectionDragging = true;
  if (event.shiftKey && calculatorState.selection) extendCellSelection(rowIndex, key);
  else setSingleCellSelection(rowIndex, key);
  refreshSelectionClasses();
}

function handleCellMouseEnter(event) {
  if (!selectionDragging || !(event.buttons & 1)) return;
  const cell = event.currentTarget;
  extendCellSelection(Number(cell.dataset.rowIndex || 0), cell.dataset.key);
}

function handleCellFocus(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  calculatorState.selectedRowIndex = rowIndex;
  activeCell = {rowIndex, key};
  beginCellEdit();
  if (!calculatorState.selection) setSingleCellSelection(rowIndex, key);
  if (key === 'travel_element') scheduleSuggestions(rowIndex, cell.textContent || '');
  markSelectedRow(rowIndex);
  refreshFormulaBarOnly();
}

function handleCellInput(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  updateRowValue(rowIndex, key, cell.textContent || '');
  markLocalDraft();
  if (key === 'day' || key === 'from_date') refreshDateCells();
  refreshDefaultedEditableCells(rowIndex);
  refreshFormulaCells(rowIndex);
  refreshTotalsOnly();
  refreshValidationAndStatus();
  refreshFormulaBarOnly();
  if (key === 'travel_element') scheduleSuggestions(rowIndex, cell.textContent || '');
}

function handleCellKeydown(event) {
  const movement = navigationMovement(event);
  if (!movement) return;
  event.preventDefault();
  commitCellEdit();
  moveActiveCell(event.currentTarget, movement.rowDelta, movement.colDelta, event.shiftKey);
}

function navigationMovement(event) {
  if (event.key === 'ArrowRight') return {rowDelta: 0, colDelta: 1};
  if (event.key === 'ArrowLeft') return {rowDelta: 0, colDelta: -1};
  if (event.key === 'ArrowDown') return {rowDelta: 1, colDelta: 0};
  if (event.key === 'ArrowUp') return {rowDelta: -1, colDelta: 0};
  if (event.key === 'Tab') return {rowDelta: 0, colDelta: event.shiftKey ? -1 : 1};
  if (event.key === 'Enter') return {rowDelta: event.shiftKey ? -1 : 1, colDelta: 0};
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
  selectCellText(target);
}

function selectCellText(cell) {
  const range = document.createRange();
  range.selectNodeContents(cell);
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
    cell.textContent = value === null || value === undefined || value === '' ? '' : String(value);
  } else if (['formula', 'formulaPercent'].includes(columnKind(key))) {
    const override = row[formulaOverrideKey(key)];
    cell.textContent = override !== null && parseNumericInput(override) === null ? String(override) : formatFormula(row[key], columnKind(key));
  } else if (key === 'supplier_currency' || key === 'sales_currency') {
    cell.textContent = row[key] || '';
  }
  commitCellEdit();
  scheduleBackendSync(250);
}

function handleCheckboxChange(event) {
  const checkbox = event.currentTarget;
  const rowIndex = Number(checkbox.dataset.rowIndex || 0);
  const key = checkbox.dataset.key;
  recordHistory();
  updateRowValue(rowIndex, key, Boolean(checkbox.checked));
  markLocalDraft();
  scheduleBackendSync(250);
}

function columnKind(key) {
  const column = columnByKey(key);
  return column?.kind || 'text';
}

function updateRowValue(rowIndex, key, rawValue) {
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
  calculateRow(row, calculatorState.currencyRates);
  validateCalculatorState(calculatorState);
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
  const text = String(rawValue || '').trim();
  if (key === 'supplier_currency' || key === 'sales_currency') return text.toUpperCase();
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
    cell.textContent = calculatorState.rows[index].from_date || '';
  }
}

function refreshDefaultedEditableCells(rowIndex) {
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  for (const key of ['units', 'supplier_commission', 'sales_price_per_unit']) {
    const cell = document.querySelector(`td[data-row-index="${rowIndex}"][data-key="${key}"]`);
    if (!cell || document.activeElement === cell) continue;
    const value = row[key];
    cell.textContent = value === null || value === undefined || value === '' ? '' : String(value);
  }
}

function refreshFormulaCells(rowIndex) {
  const row = calculatorState.rows[rowIndex];
  for (const column of FORMULA_COLUMNS) {
    const cell = document.querySelector(`td[data-row-index="${rowIndex}"][data-key="${column.key}"]`);
    if (cell && !(activeCell && activeCell.rowIndex === rowIndex && activeCell.key === column.key && document.activeElement === cell)) {
      const override = row[formulaOverrideKey(column.key)];
      cell.textContent = override !== null && parseNumericInput(override) === null ? String(override) : formatFormula(row[column.key], column.kind);
    }
  }
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
  return String(row[column.key] ?? '');
}

function updateActiveCellFromFormulaBar(value) {
  if (!activeCell) return;
  updateRowValue(activeCell.rowIndex, activeCell.key, value);
  markLocalDraft();
  refreshDefaultedEditableCells(activeCell.rowIndex);
  refreshFormulaCells(activeCell.rowIndex);
  refreshTotalsOnly();
  refreshValidationAndStatus();
}

function restoreActiveCellFocus() {
  refreshSelectionClasses();
  if (!activeCell) return;
  const target = document.querySelector(`[data-row-index="${activeCell.rowIndex}"][data-key="${activeCell.key}"]`);
  if (!target || target.matches('input')) return;
  target.focus({preventScroll: true});
}
