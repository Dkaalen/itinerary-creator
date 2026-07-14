const MAX_CALCULATOR_ROWS = CALCULATOR_DATA_END_ROW - CALCULATOR_DATA_START_ROW + 1;

function cloneRows(rows) {
  return (rows || []).map((row) => ({...row}));
}

function createBlankRow(rowId) {
  const row = {
    row_id: String(rowId),
    day: '',
    type: '',
    from_date: '',
    to_date: '',
    from_time: '',
    to_time: '',
    supplier: '',
    travel_element: '',
    manual_booking: false,
    status: '',
    comments: '',
    non_refundable: false,
    refundable: false,
    url: '',
    gross_price_per_unit: '',
    units: '',
    supplier_commission: '',
    supplier_currency: DEFAULT_CURRENCY,
    sales_price_per_unit: '',
    sales_currency: DEFAULT_CURRENCY,
    vat25: '',
    vat15: '',
    vat12: '',
    vat0_domestic: '',
    vat0_international: ''
  };
  for (const column of FORMULA_COLUMNS) row[formulaOverrideKey(column.key)] = null;
  return row;
}

function nextRowId(rows) {
  const numericIds = rows
    .map((row) => Number.parseInt(String(row.row_id || ''), 10))
    .filter((value) => Number.isFinite(value));
  return String(numericIds.length ? Math.max(...numericIds) + 1 : rows.length + 1);
}

function addRows(rows, count) {
  const updated = [...rows].slice(0, MAX_CALCULATOR_ROWS);
  const allowed = Math.max(0, Math.min(Number(count || 0), MAX_CALCULATOR_ROWS - updated.length));
  for (let index = 0; index < allowed; index += 1) {
    updated.push(createBlankRow(nextRowId(updated)));
  }
  return updated;
}

function normalizeRowsForPython(rows) {
  return rows.map((row, index) => {
    const clean = {...row, row_id: String(row.row_id || index + 1)};
    if (clean._sales_price_per_unit_touched === false) clean.sales_price_per_unit = null;
    for (const column of FORMULA_COLUMNS) delete clean[column.key];
    for (const key of Object.keys(clean)) {
      if (key.startsWith('_')) delete clean[key];
    }
    return clean;
  });
}

function currentStateSnapshot() {
  return {
    rows: normalizeRowsForPython(calculatorState.rows),
    numberOfPax: calculatorState.numberOfPax,
    showAdvanced: calculatorState.showAdvanced,
    selectedRowIndex: calculatorState.selectedRowIndex,
    activeCell: activeCell ? {...activeCell} : null,
    selection: calculatorState.selection ? {...calculatorState.selection} : null,
    columnWidths: {...(calculatorState.columnWidths || {})}
  };
}

function restoreStateSnapshot(snapshot) {
  calculatorState.rows = calculateRows(cloneRows(snapshot.rows || []), calculatorState.currencyRates);
  calculatorState.numberOfPax = snapshot.numberOfPax ?? null;
  calculatorState.showAdvanced = Boolean(snapshot.showAdvanced);
  calculatorState.selectedRowIndex = Number(snapshot.selectedRowIndex || 0);
  activeCell = snapshot.activeCell ? {...snapshot.activeCell} : null;
  calculatorState.selection = snapshot.selection ? {...snapshot.selection} : null;
  calculatorState.columnWidths = {...(snapshot.columnWidths || {})};
}
