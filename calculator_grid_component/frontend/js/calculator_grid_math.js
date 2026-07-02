const DEFAULT_RATES = {EUR: 11.3, SEK: 1.02, DKK: 1.5, ISK: 0.075, NOK: 1, USD: 10.6};
const DEFAULT_CURRENCY = 'EUR';

function numberValue(value) {
  if (value === null || value === undefined || value === '') return 0;
  const text = String(value).trim().replace('%', '').replace(',', '.');
  if (['none', 'nan', 'null'].includes(text.toLowerCase())) return 0;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : 0;
}

function optionalNumberValue(value) {
  if (value === null || value === undefined || value === '') return null;
  const text = String(value).trim();
  if (['none', 'nan', 'null'].includes(text.toLowerCase())) return null;
  return numberValue(value);
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
    const value = row[key];
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

function calculateRow(row, rates) {
  if (!rowHasUserValues(row)) {
    for (const column of FORMULA_COLUMNS) row[column.key] = null;
    return row;
  }
  const grossPerUnit = numberValue(row.gross_price_per_unit);
  const units = numberValue(row.units);
  const supplierCommissionDecimal = numberValue(row.supplier_commission) / 100;
  const grossPrice = grossPerUnit * units;
  const netPrice = grossPrice * (1 - supplierCommissionDecimal);
  const supplierRate = currencyRate(row.supplier_currency, rates);
  const netPriceNok = netPrice * supplierRate;
  const salesOverride = optionalNumberValue(row.sales_price_per_unit);
  const salesPerUnit = salesOverride === null ? grossPerUnit : salesOverride;
  const price = salesPerUnit * units;
  const salesRate = currencyRate(row.sales_currency, rates);
  const salesNok = salesPerUnit * salesRate * units;
  const gpNok = salesNok - netPriceNok;
  const gpPercent = salesNok === 0 ? 0 : gpNok / salesNok;

  row.gross_price = grossPrice;
  row.net_price = netPrice;
  row.supplier_x_rate = supplierRate;
  row.net_price_nok = netPriceNok;
  row.calculated_sales_price_per_unit = salesPerUnit;
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
  const totals = {price: 0, sales_price_nok_total: 0, gp_nok: 0, gp_percent: 0};
  for (const row of rows) {
    totals.price += numberValue(row.price);
    totals.sales_price_nok_total += numberValue(row.sales_price_nok_total);
    totals.gp_nok += numberValue(row.gp_nok);
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
