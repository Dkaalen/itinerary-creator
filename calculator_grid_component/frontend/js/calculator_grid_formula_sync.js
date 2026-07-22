// Dedicated Calculator frontend owner.

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
