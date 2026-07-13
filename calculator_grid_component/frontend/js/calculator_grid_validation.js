const NUMERIC_COLUMN_KINDS = new Set(['number', 'numberOptional', 'percent', 'formula', 'formulaPercent']);

function validateCalculatorState(state) {
  const errors = [];
  const seenIds = new Set();
  const rates = state.currencyRates || DEFAULT_RATES;
  const evaluator = new CalculatorGridFormulaEvaluator(state.rows, rates);
  const paxText = state.numberOfPax === null || state.numberOfPax === undefined ? '' : String(state.numberOfPax).trim();
  if (paxText && positiveIntegerOrNull(paxText) === null) {
    errors.push({code: 'invalid_pax', rowIndex: -1, key: 'number_of_pax', message: 'No. of pax must be a positive whole number or blank.'});
  }

  state.rows.forEach((row, rowIndex) => {
    const rowId = String(row.row_id || rowIndex + 1).trim();
    const excelRow = CALCULATOR_DATA_START_ROW + rowIndex;
    if (seenIds.has(rowId)) {
      errors.push({code: 'duplicate_row_id', rowIndex, key: 'row_id', message: `Row ID ${rowId} is duplicated.`});
    }
    seenIds.add(rowId);

    for (const column of CALCULATOR_COLUMNS) {
      if (!NUMERIC_COLUMN_KINDS.has(column.kind)) continue;
      const storageKey = column.formula ? formulaOverrideKey(column.key) : column.key;
      const value = row[storageKey];
      if (value === null || value === undefined || String(value).trim() === '') continue;
      const excelColumn = EXCEL_COLUMN_BY_FIELD[column.key];
      if (!excelColumn) continue;
      const reference = `${excelColumn}${excelRow}`;
      try {
        evaluator.evaluateCell(reference);
      } catch (error) {
        const code = error instanceof CalculatorGridFormulaError ? error.code : '#VALUE!';
        const detail = error instanceof Error ? error.message : 'Invalid formula.';
        const validationCode = column.formula ? 'invalid_formula' : 'invalid_number';
        errors.push({code: validationCode, formulaCode: code, rowIndex, key: column.key, message: `Row ${rowId}: ${column.label} ${code} — ${detail}`});
      }
    }

    try {
      const commission = evaluator.evaluateCell(`T${excelRow}`);
      if (commission < 0 || commission > 1) {
        errors.push({code: 'invalid_commission', rowIndex, key: 'supplier_commission', message: `Row ${rowId}: supplier commission must be between 0% and 100%.`});
      }
    } catch (_error) {
      // The formula validation above already reports the invalid commission cell.
    }

    validateCurrencyRate(errors, evaluator, row, rowIndex, rowId, excelRow, 'supplier_currency', 'supplier_x_rate_override', 'W', rates);
    validateCurrencyRate(errors, evaluator, row, rowIndex, rowId, excelRow, 'sales_currency', 'sales_x_rate_override', 'AB', rates);
  });

  state.validationErrors = deduplicateValidationErrors(errors);
  return state.validationErrors;
}

function validateCurrencyRate(errors, evaluator, row, rowIndex, rowId, excelRow, currencyKey, overrideKey, excelColumn, rates) {
  const override = row[overrideKey];
  if (override !== null && override !== undefined && String(override).trim() !== '') {
    try {
      const rate = evaluator.evaluateCell(`${excelColumn}${excelRow}`);
      if (!Number.isFinite(rate) || rate <= 0) {
        errors.push({code: 'invalid_rate_override', rowIndex, key: excelColumn === 'W' ? 'supplier_x_rate' : 'sales_x_rate', message: `Row ${rowId}: manual exchange rate must be greater than zero.`});
      }
    } catch (_error) {
      // Formula validation reports the detailed cell error.
    }
    return;
  }
  const code = currencyCode(row[currencyKey]);
  const rate = Number(rates[code]);
  if (!Number.isFinite(rate) || rate <= 0) {
    errors.push({code: 'missing_rate', rowIndex, key: currencyKey, message: `Row ${rowId}: no positive NOK exchange rate exists for ${code}.`});
  }
}

function deduplicateValidationErrors(errors) {
  const seen = new Set();
  return errors.filter((error) => {
    const key = `${error.code}:${error.rowIndex}:${error.key}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function validationErrorForCell(rowIndex, key) {
  return (calculatorState?.validationErrors || []).find((error) => error.rowIndex === rowIndex && error.key === key) || null;
}

function hasBlockingValidationErrors() {
  return validateCalculatorState(calculatorState).length > 0;
}

function validationSummaryHtml(state) {
  const errors = state.validationErrors || [];
  if (!errors.length) return '';
  const first = errors.slice(0, 4).map((error) => `<li>${escapeHtml(error.message)}</li>`).join('');
  const extra = errors.length > 4 ? `<li>And ${errors.length - 4} more issue(s).</li>` : '';
  return `<div class="calculator-validation-panel"><strong>Fix these cells before saving, exporting, or leaving:</strong><ul>${first}${extra}</ul></div>`;
}
