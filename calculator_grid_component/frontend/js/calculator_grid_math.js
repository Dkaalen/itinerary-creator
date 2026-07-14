const DEFAULT_RATES = {NOK: 1, EUR: 11, USD: 10, GBP: 13, DKK: 1.5, SEK: 1, ISK: 0.08, CHF: 12, CAD: 7.5, AUD: 7, PLN: 2.5, JPY: 0.07};
const DEFAULT_CURRENCY = 'EUR';
const CALCULATOR_DATA_START_ROW = 7;
const CALCULATOR_DATA_END_ROW = 99;

const NUMERIC_FIELD_BY_EXCEL_COLUMN = {
  Q: 'gross_price_per_unit',
  R: 'units',
  T: 'supplier_commission',
  AF: 'vat25',
  AG: 'vat15',
  AH: 'vat12',
  AI: 'vat0_domestic',
  AJ: 'vat0_international'
};
const FORMULA_FIELD_BY_EXCEL_COLUMN = {
  S: 'gross_price',
  U: 'net_price',
  W: 'supplier_x_rate',
  X: 'net_price_nok',
  Z: 'price',
  AB: 'sales_x_rate',
  AC: 'sales_price_nok_total',
  AD: 'gp_nok',
  AE: 'gp_percent'
};
const EXCEL_COLUMN_BY_FIELD = Object.fromEntries([
  ...Object.entries(NUMERIC_FIELD_BY_EXCEL_COLUMN),
  ...Object.entries(FORMULA_FIELD_BY_EXCEL_COLUMN),
  ['Y', 'sales_price_per_unit']
].map(([column, field]) => [field, column]));

class CalculatorGridFormulaError extends Error {
  constructor(code, message, cell = '') {
    super(message);
    this.code = code;
    this.cell = cell;
  }
}

function numberValue(value) {
  const parsed = parseNumericInput(value);
  return parsed === null ? 0 : parsed;
}

function optionalNumberValue(value) {
  if (value === null || value === undefined || value === '') return null;
  const text = String(value).trim();
  if (['none', 'nan', 'null'].includes(text.toLowerCase())) return null;
  return parseNumericInput(value);
}

function roundHalfAwayFromZero(value, digits) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  const factor = 10 ** digits;
  const scaled = Math.abs(number) * factor;
  const tolerance = Number.EPSILON * Math.max(1, scaled) * 4;
  const magnitude = Math.floor(scaled + 0.5 + tolerance) / factor;
  return number < 0 ? -magnitude : magnitude;
}

function roundMoney(value) {
  return roundHalfAwayFromZero(value, 2);
}

function roundRate(value) {
  return roundHalfAwayFromZero(value, 6);
}

function roundPercent(value) {
  return roundHalfAwayFromZero(value, 6);
}

function currencyCode(value) {
  const text = String(value || '').trim().toUpperCase();
  return text || DEFAULT_CURRENCY;
}

function currencyRate(value, rates) {
  const code = currencyCode(value);
  return roundRate(numberValue((rates || DEFAULT_RATES)[code]));
}

function salesPriceWasTouched(row) {
  if (typeof row?._sales_price_per_unit_touched === 'boolean') return row._sales_price_per_unit_touched;
  const raw = row?.sales_price_per_unit;
  if (raw === null || raw === undefined || String(raw).trim() === '') return false;
  const parsed = optionalNumberValue(raw);
  return !(parsed === 0 && numberValue(row?.gross_price_per_unit) > 0);
}

function rowHasUserValues(row) {
  const ignore = new Set(['row_id', 'supplier_currency', 'sales_currency']);
  for (const key of ALL_EDITABLE_KEYS) {
    if (ignore.has(key)) continue;
    const column = columnByKey(key);
    if (column?.formula && (row[formulaOverrideKey(key)] === null || row[formulaOverrideKey(key)] === undefined)) continue;
    const value = column?.formula ? row[formulaOverrideKey(key)] : row[key];
    if (typeof value === 'boolean') {
      if (value) return true;
    } else if (typeof value === 'number') {
      if (value !== 0) return true;
    } else if (String(value ?? '').trim() !== '') {
      return true;
    }
  }
  return false;
}

class CalculatorGridFormulaEvaluator {
  constructor(rows, rates) {
    this.rows = rows || [];
    this.rates = rates || DEFAULT_RATES;
    this.cache = new Map();
    this.visiting = [];
    this.errors = {};
  }

  evaluateExpression(value, currentCell = '') {
    try {
      const result = evaluateNumericInput(value, (reference) => this.evaluateCell(reference));
      return result === null ? 0 : result;
    } catch (error) {
      if (error instanceof CalculatorGridFormulaError) throw error;
      const code = String(error?.message || '').startsWith('#') ? String(error.message) : '#VALUE!';
      throw new CalculatorGridFormulaError(code, `${currentCell || 'Formula'} is invalid.`, currentCell);
    }
  }

  evaluateCell(reference) {
    const normalized = String(reference || '').replaceAll('$', '').toUpperCase();
    if (this.cache.has(normalized)) return this.cache.get(normalized);
    const match = normalized.match(/^([A-Z]{1,2})(\d+)$/);
    if (!match) throw new CalculatorGridFormulaError('#REF!', `Invalid reference ${reference}.`, normalized);
    const column = match[1];
    const rowNumber = Number(match[2]);
    if (rowNumber < CALCULATOR_DATA_START_ROW || rowNumber > CALCULATOR_DATA_END_ROW) {
      throw new CalculatorGridFormulaError('#REF!', `${normalized} is outside calculator rows.`, normalized);
    }
    const rowIndex = rowNumber - CALCULATOR_DATA_START_ROW;
    if (rowIndex >= this.rows.length) return 0;
    const cycleIndex = this.visiting.indexOf(normalized);
    if (cycleIndex >= 0) {
      const cycle = [...this.visiting.slice(cycleIndex), normalized].join(' → ');
      throw new CalculatorGridFormulaError('#CIRC!', `Circular reference: ${cycle}.`, normalized);
    }
    this.visiting.push(normalized);
    try {
      const result = this.evaluateCellValue(column, rowNumber, this.rows[rowIndex]);
      this.cache.set(normalized, result);
      return result;
    } finally {
      this.visiting.pop();
    }
  }

  evaluateCellValue(column, rowNumber, row) {
    const ref = `${column}${rowNumber}`;
    const inputField = NUMERIC_FIELD_BY_EXCEL_COLUMN[column];
    if (inputField) {
      const value = this.evaluateExpression(row[inputField], ref);
      // The grid displays commission as percentage points while Excel/Python stores a decimal.
      return column === 'T' ? value / 100 : value;
    }
    if (column === 'Y') {
      const gross = this.evaluateCell(`Q${rowNumber}`);
      const raw = row.sales_price_per_unit;
      const defaultValue = this.defaultSalesPricePerUnit(rowNumber, row);
      if (!salesPriceWasTouched(row) || raw === null || raw === undefined || String(raw).trim() === '') return defaultValue;
      const value = this.evaluateExpression(raw, ref);
      return value === 0 && gross > 0 ? defaultValue : value;
    }

    const formulaField = FORMULA_FIELD_BY_EXCEL_COLUMN[column];
    if (formulaField) {
      const override = row[formulaOverrideKey(formulaField)];
      if (override !== null && override !== undefined && String(override).trim() !== '') {
        const value = this.evaluateExpression(override, ref);
        if (column === 'W' || column === 'AB') return roundRate(value);
        if (column === 'AE') return roundPercent(value);
        return roundMoney(value);
      }
    }

    if (column === 'S') return roundMoney(this.evaluateCell(`Q${rowNumber}`) * this.evaluateCell(`R${rowNumber}`));
    if (column === 'U') return roundMoney(this.evaluateCell(`S${rowNumber}`) * (1 - roundPercent(this.evaluateCell(`T${rowNumber}`))));
    if (column === 'W') return currencyRate(row.supplier_currency, this.rates);
    if (column === 'X') return roundMoney(this.evaluateCell(`U${rowNumber}`) * this.evaluateCell(`W${rowNumber}`));
    if (column === 'Z') return roundMoney(this.evaluateCell(`Y${rowNumber}`) * this.evaluateCell(`R${rowNumber}`));
    if (column === 'AB') return currencyRate(row.sales_currency, this.rates);
    if (column === 'AC') return roundMoney(this.evaluateCell(`Z${rowNumber}`) * this.evaluateCell(`AB${rowNumber}`));
    if (column === 'AD') return roundMoney(this.evaluateCell(`AC${rowNumber}`) - this.evaluateCell(`X${rowNumber}`));
    if (column === 'AE') {
      const sales = this.evaluateCell(`AC${rowNumber}`);
      return sales === 0 ? 0 : this.evaluateCell(`AD${rowNumber}`) / sales;
    }
    throw new CalculatorGridFormulaError('#VALUE!', `${ref} is text or unsupported.`, ref);
  }

  defaultSalesPricePerUnit(rowNumber, row) {
    const gross = this.evaluateCell(`Q${rowNumber}`);
    const supplierRate = this.evaluateCell(`W${rowNumber}`);
    const salesRate = this.evaluateCell(`AB${rowNumber}`);
    if (salesRate === 0) return 0;
    return gross * supplierRate / salesRate;
  }

  errorForCell(reference, error) {
    const normalized = String(reference || '').replaceAll('$', '').toUpperCase();
    const formulaError = error instanceof CalculatorGridFormulaError
      ? error
      : new CalculatorGridFormulaError('#VALUE!', `${normalized} is invalid.`, normalized);
    this.errors[normalized] = {code: formulaError.code, message: formulaError.message, cell: normalized};
    return formulaError.code;
  }
}

function calculateRow(row, rates) {
  return calculateRows([row], rates)[0];
}

function calculateRows(rows, rates) {
  const evaluator = new CalculatorGridFormulaEvaluator(rows, rates);
  rows.forEach((row, index) => {
    row._formula_errors = {};
    const rowNumber = CALCULATOR_DATA_START_ROW + index;
    if (!rowHasUserValues(row)) {
      for (const column of FORMULA_COLUMNS) row[column.key] = null;
      return;
    }

    const grossReference = `Q${rowNumber}`;
    let gross = 0;
    try {
      gross = evaluator.evaluateCell(grossReference);
    } catch (error) {
      row._formula_errors[grossReference] = evaluator.errorForCell(grossReference, error);
    }
    row._sales_price_per_unit_touched = salesPriceWasTouched(row);
    if (!row._sales_price_per_unit_touched && gross !== 0) {
      try {
        row.sales_price_per_unit = evaluator.defaultSalesPricePerUnit(rowNumber, row);
        evaluator.cache.delete(`Y${rowNumber}`);
      } catch (error) {
        const reference = `Y${rowNumber}`;
        row._formula_errors[reference] = evaluator.errorForCell(reference, error);
      }
    }

    for (const [column, field] of Object.entries(FORMULA_FIELD_BY_EXCEL_COLUMN)) {
      const reference = `${column}${rowNumber}`;
      try {
        row[field] = evaluator.evaluateCell(reference);
      } catch (error) {
        const code = evaluator.errorForCell(reference, error);
        row[field] = code;
        row._formula_errors[reference] = code;
      }
    }
  });
  if (typeof calculatorState !== 'undefined' && calculatorState) calculatorState.formulaErrors = evaluator.errors;
  return rows;
}

function calculateTotals(rows) {
  const totals = {
    price: 0,
    net_price_nok: 0,
    sales_price_nok_total: 0,
    gp_nok: 0,
    gp_percent: 0,
    vat25: 0,
    vat15: 0,
    vat12: 0,
    vat0_domestic: 0,
    vat0_international: 0
  };
  for (const row of rows) {
    totals.price += numberValue(row.price);
    totals.net_price_nok += numberValue(row.net_price_nok);
    totals.sales_price_nok_total += numberValue(row.sales_price_nok_total);
    totals.gp_nok += numberValue(row.gp_nok);
    totals.vat25 += numberValue(row.vat25);
    totals.vat15 += numberValue(row.vat15);
    totals.vat12 += numberValue(row.vat12);
    totals.vat0_domestic += numberValue(row.vat0_domestic);
    totals.vat0_international += numberValue(row.vat0_international);
  }
  for (const key of ['price', 'net_price_nok', 'sales_price_nok_total', 'gp_nok', 'vat25', 'vat15', 'vat12', 'vat0_domestic', 'vat0_international']) {
    totals[key] = roundMoney(totals[key]);
  }
  totals.gp_percent = totals.sales_price_nok_total === 0 ? 0 : totals.gp_nok / totals.sales_price_nok_total;
  return totals;
}

function calculateDashboard(state) {
  const totals = calculateTotals(state.rows);
  const pax = positiveIntegerOrNull(state.numberOfPax);
  return {
    ...totals,
    number_of_pax: pax,
    cost_per_pax: pax ? roundMoney(totals.net_price_nok / pax) : null,
    sales_per_pax: pax ? roundMoney(totals.sales_price_nok_total / pax) : null,
    currency_exposure: calculateCurrencyExposure(state.rows)
  };
}

function calculateCurrencyExposure(rows) {
  const supplier = {};
  const sales = {};
  for (const row of rows || []) {
    const supplierCurrency = String(row.supplier_currency || DEFAULT_CURRENCY).toUpperCase();
    const salesCurrency = String(row.sales_currency || DEFAULT_CURRENCY).toUpperCase();
    supplier[supplierCurrency] = roundMoney((supplier[supplierCurrency] || 0) + numberValue(row.net_price));
    sales[salesCurrency] = roundMoney((sales[salesCurrency] || 0) + numberValue(row.price));
  }
  return {
    supplier: Object.entries(supplier).filter(([, value]) => value !== 0).sort(([left], [right]) => left.localeCompare(right)),
    sales: Object.entries(sales).filter(([, value]) => value !== 0).sort(([left], [right]) => left.localeCompare(right))
  };
}

function positiveIntegerOrNull(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : null;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string' && value.startsWith('#')) return value;
  const number = numberValue(value);
  if (!Number.isFinite(number)) return '';
  return number.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});
}

function formatFormula(value, kind) {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string' && value.startsWith('#')) return value;
  if (kind === 'formulaPercent') return `${(numberValue(value) * 100).toFixed(1)}%`;
  return formatNumber(value, 2);
}
