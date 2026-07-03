function handleCellFocus(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  calculatorState.selectedRowIndex = rowIndex;
  activeCell = {rowIndex, key};
  if (key === 'travel_element') scheduleSuggestions(rowIndex, cell.textContent || '');
  markSelectedRow(rowIndex);
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
  if (key === 'travel_element') {
    scheduleSuggestions(rowIndex, cell.textContent || '');
  }
}

function handleCellKeydown(event) {
  const movement = navigationMovement(event);
  if (!movement) return;
  event.preventDefault();
  moveActiveCell(event.currentTarget, movement.rowDelta, movement.colDelta);
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

function moveActiveCell(cell, rowDelta, colDelta) {
  const columns = visibleColumns(calculatorState.showAdvanced);
  const currentRowIndex = Number(cell.dataset.rowIndex || 0);
  const currentKey = cell.dataset.key;
  const currentColIndex = columns.findIndex((column) => column.key === currentKey);
  if (currentColIndex < 0) return;
  const targetRowIndex = Math.max(0, Math.min(calculatorState.rows.length - 1, currentRowIndex + rowDelta));
  const targetColIndex = Math.max(0, Math.min(columns.length - 1, currentColIndex + colDelta));
  const targetKey = columns[targetColIndex].key;
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
    cell.textContent = formatFormula(row[key], columnKind(key));
  } else if (key === 'supplier_currency' || key === 'sales_currency') {
    cell.textContent = row[key] || '';
  }
}

function handleCheckboxChange(event) {
  const checkbox = event.currentTarget;
  const rowIndex = Number(checkbox.dataset.rowIndex || 0);
  const key = checkbox.dataset.key;
  updateRowValue(rowIndex, key, Boolean(checkbox.checked));
  markLocalDraft();
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
  else if (kind === 'numberOptional') row[key] = optionalNumberValue(rawValue);
  else if (kind === 'formula' || kind === 'formulaPercent') {
    row[formulaOverrideKey(key)] = formulaOverrideValue(rawValue, kind);
  } else if (kind === 'percent') row[key] = rawValue === '' ? '' : percentPointInputValue(rawValue);
  else if (kind === 'number') row[key] = rawValue === '' ? '' : numberValue(rawValue);
  else row[key] = normalizedTextValue(key, rawValue);
  if (key === 'day' || key === 'from_date') autofillDatesFromArrival(calculatorState.rows);
  calculateRow(row, calculatorState.currencyRates);
}

function normalizedTextValue(key, rawValue) {
  const text = String(rawValue || '').trim();
  if (key === 'supplier_currency' || key === 'sales_currency') return text.toUpperCase();
  return text;
}

function formulaOverrideValue(rawValue, kind) {
  if (rawValue === null || rawValue === undefined || String(rawValue).trim() === '') return null;
  if (kind === 'formulaPercent') return percentInputValue(rawValue);
  return numberValue(rawValue);
}

function percentInputValue(rawValue) {
  const text = String(rawValue || '').trim();
  const number = numberValue(rawValue);
  return text.includes('%') ? number : number / 100;
}

function percentPointInputValue(rawValue) {
  const text = String(rawValue || '').trim();
  const number = numberValue(rawValue);
  return text.includes('%') ? number * 100 : number;
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
      cell.textContent = formatFormula(row[column.key], column.kind);
    }
  }
}

function refreshTotalsOnly() {
  const totalsPanel = document.querySelector('.calculator-totals-panel');
  if (!totalsPanel) return;
  const totals = calculateTotals(calculatorState.rows);
  totalsPanel.innerHTML = `
    <span>Total price: <strong>${formatNumber(totals.price, 0)}</strong></span>
    <span>Total sales NOK: <strong>${formatNumber(totals.sales_price_nok_total, 0)}</strong></span>
    <span>Total net NOK: <strong>${formatNumber(totals.net_price_nok, 0)}</strong></span>
    <span>Earnings / GP NOK: <strong>${formatNumber(totals.gp_nok, 0)}</strong></span>
    <span>GP %: <strong>${(totals.gp_percent * 100).toFixed(1)}%</strong></span>
    <span>VAT25: <strong>${formatNumber(totals.vat25, 0)}</strong></span>
    <span>VAT15: <strong>${formatNumber(totals.vat15, 0)}</strong></span>
    <span>VAT12: <strong>${formatNumber(totals.vat12, 0)}</strong></span>
    <span>VAT0-D: <strong>${formatNumber(totals.vat0_domestic, 0)}</strong></span>
    <span>VAT0-I: <strong>${formatNumber(totals.vat0_international, 0)}</strong></span>`;
}
