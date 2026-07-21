const NUMERIC_COLUMN_KINDS = new Set(['number', 'numberOptional', 'percent', 'formula', 'formulaPercent']);
const CALCULATOR_VALIDATION_SCOPE = Object.freeze({
  DISPLAY: 'display',
  DRAFT_SAFE: 'draft_safe',
  PERSISTENCE: 'persistence',
  EXPORT: 'export',
  GENERATION: 'generation',
  IMPORT: 'import'
});

function calculatorValidationErrors(state, scope = CALCULATOR_VALIDATION_SCOPE.DISPLAY) {
  if (scope === CALCULATOR_VALIDATION_SCOPE.DRAFT_SAFE || scope === CALCULATOR_VALIDATION_SCOPE.IMPORT) return [];
  if (scope === CALCULATOR_VALIDATION_SCOPE.GENERATION) return generationValidationErrors(state);
  if (scope === CALCULATOR_VALIDATION_SCOPE.PERSISTENCE) return persistenceValidationErrors(state);

  const errors = [];
  const seenIds = new Set();
  const rates = state.currencyRates || DEFAULT_RATES;
  const evaluator = new CalculatorGridFormulaEvaluator(state.rows, rates);
  const paxText = state.numberOfPax === null || state.numberOfPax === undefined ? '' : String(state.numberOfPax).trim();
  if (scope === CALCULATOR_VALIDATION_SCOPE.DISPLAY && paxText && positiveIntegerOrNull(paxText) === null) {
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

  return deduplicateValidationErrors(errors);
}

function validateCalculatorState(state, scope = CALCULATOR_VALIDATION_SCOPE.DISPLAY) {
  state.validationErrors = calculatorValidationErrors(state, scope);
  return state.validationErrors;
}

function validationScopeForAction(action) {
  if (action === 'close' || action === 'open_library') return CALCULATOR_VALIDATION_SCOPE.DRAFT_SAFE;
  if (action === 'download') return CALCULATOR_VALIDATION_SCOPE.EXPORT;
  if (action === 'generate_agent' || action === 'generate_customer') return CALCULATOR_VALIDATION_SCOPE.GENERATION;
  if (action === 'open_excel') return CALCULATOR_VALIDATION_SCOPE.IMPORT;
  return CALCULATOR_VALIDATION_SCOPE.PERSISTENCE;
}

function persistenceValidationErrors(state) {
  const errors = [];
  const evaluator = new CalculatorGridFormulaEvaluator(state.rows, state.currencyRates || DEFAULT_RATES);
  const paxText = state.numberOfPax === null || state.numberOfPax === undefined ? '' : String(state.numberOfPax).trim();
  if (paxText && positiveIntegerOrNull(paxText) === null) {
    errors.push({code: 'invalid_pax', rowIndex: -1, key: 'number_of_pax', message: 'No. of pax must be a positive whole number or blank before saving.'});
  }
  const seenIds = new Set();
  state.rows.forEach((row, rowIndex) => {
    const rowId = String(row.row_id || rowIndex + 1).trim();
    if (seenIds.has(rowId)) {
      errors.push({code: 'duplicate_row_id', rowIndex, key: 'row_id', message: `Row ID ${rowId} is duplicated.`});
    }
    seenIds.add(rowId);
    for (const column of CALCULATOR_COLUMNS) {
      if (!NUMERIC_COLUMN_KINDS.has(column.kind)) continue;
      const storageKey = column.formula ? formulaOverrideKey(column.key) : column.key;
      const value = row[storageKey];
      if (value === null || value === undefined || String(value).trim() === '') continue;
      if (typeof value === 'number' && !Number.isFinite(value)) {
        errors.push({code: 'non_persistable_number', rowIndex, key: column.key, message: `Row ${rowId}: ${column.label} must be finite or contain a formula before saving.`});
        continue;
      }
      const excelColumn = EXCEL_COLUMN_BY_FIELD[column.key];
      if (!excelColumn) continue;
      try {
        evaluator.evaluateCell(`${excelColumn}${CALCULATOR_DATA_START_ROW + rowIndex}`);
      } catch (error) {
        const formulaCode = error instanceof CalculatorGridFormulaError ? error.code : '#VALUE!';
        const detail = error instanceof Error ? error.message : 'Invalid formula.';
        errors.push({code: column.formula ? 'invalid_formula' : 'invalid_number', formulaCode, rowIndex, key: column.key, message: `Row ${rowId}: ${column.label} ${formulaCode} — ${detail}`});
      }
    }
  });
  return deduplicateValidationErrors(errors);
}

function generationValidationErrors(state) {
  const errors = [];
  let completeRows = 0;
  const contentKeys = ['day', 'type', 'from_date', 'to_date', 'from_time', 'to_time', 'supplier', 'travel_element', 'comments', 'url'];
  state.rows.forEach((row, rowIndex) => {
    const rowId = String(row.row_id || rowIndex + 1).trim();
    const rowType = String(row.type || '').trim();
    const travelElement = String(row.travel_element || '').trim();
    if (!contentKeys.some((key) => String(row[key] || '').trim())) return;
    if (['', 'total', 'subtotal', 'sub total'].includes(rowType.toLowerCase())) {
      if (!rowType) {
        errors.push({code: 'missing_generation_type', rowIndex, key: 'type', message: `Row ${rowId}: Type is required before generating an itinerary.`});
      }
      return;
    }
    if (!travelElement) {
      errors.push({code: 'missing_generation_travel_element', rowIndex, key: 'travel_element', message: `Row ${rowId}: Travel element is required before generating an itinerary.`});
      return;
    }
    completeRows += 1;
  });
  if (completeRows === 0 && errors.length === 0) {
    errors.push({code: 'no_generatable_rows', rowIndex: -1, key: 'travel_element', message: 'Add at least one calculator row with both Type and Travel element before generating an itinerary.'});
  }
  return deduplicateValidationErrors(errors);
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
  return `<div class="calculator-validation-panel"><strong>Some cells need attention for this action:</strong><ul>${first}${extra}</ul></div>`;
}
