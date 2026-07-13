const DEFAULT_RATES = {NOK: 1, EUR: 11, USD: 10, GBP: 13, DKK: 1.5, SEK: 1, ISK: 0.08, CHF: 12, CAD: 7.5, AUD: 7, PLN: 2.5, JPY: 0.07};
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

function roundHalfAwayFromZero(value, digits) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  const factor = 10 ** digits;
  const scaled = Math.abs(number) * factor;
  // Decimal-looking inputs often land microscopically below an exact .5 after
  // JavaScript multiplication. Use a magnitude-aware machine tolerance so the
  // preview matches Excel ROUND and the canonical Python Decimal engine.
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
  if (override === null) return calculated;
  if (key === 'supplier_x_rate' || key === 'sales_x_rate') return roundRate(override);
  if (key === 'gp_percent') return roundPercent(override);
  return roundMoney(override);
}

function calculateRow(row, rates) {
  if (!rowHasUserValues(row)) {
    for (const column of FORMULA_COLUMNS) row[column.key] = null;
    return row;
  }
  const grossPerUnit = numberValue(row.gross_price_per_unit);
  const units = numberValue(row.units);
  const supplierCommissionDecimal = roundPercent(numberValue(row.supplier_commission) / 100);
  const grossPrice = formulaValue(row, 'gross_price', roundMoney(grossPerUnit * units));
  const netPrice = formulaValue(row, 'net_price', roundMoney(grossPrice * (1 - supplierCommissionDecimal)));
  const supplierRate = formulaValue(row, 'supplier_x_rate', currencyRate(row.supplier_currency, rates));
  const netPriceNok = formulaValue(row, 'net_price_nok', roundMoney(netPrice * supplierRate));
  const salesPerUnit = salesPricePerUnit(row, grossPerUnit);
  row.sales_price_per_unit = grossPerUnit === 0 && !row._sales_price_per_unit_touched ? '' : salesPerUnit;
  const price = formulaValue(row, 'price', roundMoney(salesPerUnit * units));
  const salesRate = formulaValue(row, 'sales_x_rate', currencyRate(row.sales_currency, rates));
  const salesNok = formulaValue(row, 'sales_price_nok_total', roundMoney(price * salesRate));
  const gpNok = formulaValue(row, 'gp_nok', roundMoney(salesNok - netPriceNok));
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

function salesPricePerUnit(row, grossPerUnit) {
  const salesOverride = optionalNumberValue(row.sales_price_per_unit);
  if (!row._sales_price_per_unit_touched && (salesOverride === null || salesOverride === 0) && grossPerUnit > 0) {
    return grossPerUnit;
  }
  return salesOverride === null ? grossPerUnit : salesOverride;
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
    sales_per_pax: pax ? roundMoney(totals.sales_price_nok_total / pax) : null
  };
}

function positiveIntegerOrNull(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : null;
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
  if (kind === 'formula' && Math.abs(numberValue(value)) < 100) return formatNumber(value, 2);
  return formatNumber(value, 2);
}
