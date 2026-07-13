const NUMERIC_COLUMN_KINDS = new Set(['number', 'numberOptional', 'percent', 'formula', 'formulaPercent']);

function validateCalculatorState(state) {
  const errors = [];
  const seenIds = new Set();
  const rates = state.currencyRates || DEFAULT_RATES;
  const paxText = state.numberOfPax === null || state.numberOfPax === undefined ? '' : String(state.numberOfPax).trim();
  if (paxText && positiveIntegerOrNull(paxText) === null) {
    errors.push({code: 'invalid_pax', rowIndex: -1, key: 'number_of_pax', message: 'No. of pax must be a positive whole number or blank.'});
  }

  state.rows.forEach((row, rowIndex) => {
    const rowId = String(row.row_id || rowIndex + 1).trim();
    if (seenIds.has(rowId)) {
      errors.push({code: 'duplicate_row_id', rowIndex, key: 'row_id', message: `Row ID ${rowId} is duplicated.`});
    }
    seenIds.add(rowId);

    for (const column of CALCULATOR_COLUMNS) {
      if (!NUMERIC_COLUMN_KINDS.has(column.kind)) continue;
      const key = column.formula ? formulaOverrideKey(column.key) : column.key;
      const value = row[key];
      if (value === null || value === undefined || String(value).trim() === '') continue;
      if (parseNumericInput(value) === null) {
        errors.push({code: 'invalid_number', rowIndex, key: column.key, message: `Row ${rowId}: ${column.label} is not a valid number or arithmetic expression.`});
      }
    }

    const commissionText = row.supplier_commission;
    if (commissionText !== null && commissionText !== undefined && String(commissionText).trim() !== '') {
      const commission = parseNumericInput(commissionText);
      if (commission !== null && (commission < 0 || commission > 100)) {
        errors.push({code: 'invalid_commission', rowIndex, key: 'supplier_commission', message: `Row ${rowId}: supplier commission must be between 0% and 100%.`});
      }
    }

    validateCurrencyRate(errors, row, rowIndex, rowId, 'supplier_currency', 'supplier_x_rate_override', rates);
    validateCurrencyRate(errors, row, rowIndex, rowId, 'sales_currency', 'sales_x_rate_override', rates);
  });

  state.validationErrors = errors;
  return errors;
}

function validateCurrencyRate(errors, row, rowIndex, rowId, currencyKey, overrideKey, rates) {
  const override = optionalNumberValue(row[overrideKey]);
  if (override !== null) {
    if (!Number.isFinite(override) || override <= 0) {
      errors.push({code: 'invalid_rate_override', rowIndex, key: currencyKey === 'supplier_currency' ? 'supplier_x_rate' : 'sales_x_rate', message: `Row ${rowId}: manual exchange rate must be greater than zero.`});
    }
    return;
  }
  const code = currencyCode(row[currencyKey]);
  const rate = Number(rates[code]);
  if (!Number.isFinite(rate) || rate <= 0) {
    errors.push({code: 'missing_rate', rowIndex, key: currencyKey, message: `Row ${rowId}: no positive NOK exchange rate exists for ${code}.`});
  }
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
