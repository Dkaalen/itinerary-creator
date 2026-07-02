const DEFAULT_RATES = {EUR: 11.3, SEK: 1.02, DKK: 1.5, ISK: 0.075, NOK: 1, USD: 10.6};
const DEFAULT_CURRENCY = 'EUR';

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

function currencyCode(value) {
  const text = String(value || '').trim().toUpperCase();
  return text || DEFAULT_CURRENCY;
}

function currencyRate(value, rates) {
  const code = currencyCode(value);
  return numberValue((rates || DEFAULT_RATES)[code]);
}

function rowHasUserValues(row) {
  const ignore = new Set(['row_id', 'supplier_currency', 'sales_currency']);
  for (const key of ALL_EDITABLE_KEYS) {
    if (ignore.has(key)) continue;
    const column = columnByKey(key);
    if (column?.formula && row[formulaOverrideKey(key)] === null) continue;
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

function formulaValue(row, key, calculated) {
  const override = optionalNumberValue(row[formulaOverrideKey(key)]);
  return override === null ? calculated : override;
}

function calculateRow(row, rates) {
  if (!rowHasUserValues(row)) {
    for (const column of FORMULA_COLUMNS) row[column.key] = null;
    return row;
  }
  const grossPerUnit = numberValue(row.gross_price_per_unit);
  const units = numberValue(row.units);
  const supplierCommissionDecimal = numberValue(row.supplier_commission) / 100;
  const grossPrice = formulaValue(row, 'gross_price', grossPerUnit * units);
  const netPrice = formulaValue(row, 'net_price', grossPrice * (1 - supplierCommissionDecimal));
  const supplierRate = formulaValue(row, 'supplier_x_rate', currencyRate(row.supplier_currency, rates));
  const netPriceNok = formulaValue(row, 'net_price_nok', netPrice * supplierRate);
  const salesOverride = optionalNumberValue(row.sales_price_per_unit);
  const salesPerUnit = salesOverride === null ? grossPerUnit : salesOverride;
  const price = formulaValue(row, 'price', salesPerUnit * units);
  const salesRate = formulaValue(row, 'sales_x_rate', currencyRate(row.sales_currency, rates));
  const salesNok = formulaValue(row, 'sales_price_nok_total', salesPerUnit * salesRate * units);
  const gpNok = formulaValue(row, 'gp_nok', salesNok - netPriceNok);
  const gpPercent = formulaValue(row, 'gp_percent', salesNok === 0 ? 0 : gpNok / salesNok);

  row.gross_price = grossPrice;
  row.net_price = netPrice;
  row.supplier_x_rate = supplierRate;
  row.net_price_nok = netPriceNok;
  row.price = price;
  row.sales_x_rate = salesRate;
  row.sales_price_nok_total = salesNok;
  row.gp_nok = gpNok;
  row.gp_percent = gpPercent;
  return row;
}

function calculateRows(rows, rates) {
  return rows.map((row) => calculateRow(row, rates));
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
  totals.gp_percent = totals.sales_price_nok_total === 0 ? 0 : totals.gp_nok / totals.sales_price_nok_total;
  return totals;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '';
  const number = numberValue(value);
  if (!Number.isFinite(number)) return '';
  return number.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});
}

function formatFormula(value, kind) {
  if (value === null || value === undefined || value === '') return '';
  if (kind === 'formulaPercent') return `${(numberValue(value) * 100).toFixed(1)}%`;
  return formatNumber(value, 2);
}
