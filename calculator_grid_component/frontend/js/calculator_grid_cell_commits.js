// Dedicated Calculator frontend owner.

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
  if (key === 'sales_price_per_unit') row._sales_price_per_unit_touched = String(rawValue ?? '').trim() !== '';
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
