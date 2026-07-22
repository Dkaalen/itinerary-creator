// Currency defaults, conversion, and exposure.

function currencyCode(value) {
  const text = String(value || '').trim().toUpperCase();
  return text || DEFAULT_CURRENCY;
}

function currencyRate(value, rates) {
  const code = currencyCode(value);
  return roundRate(numberValue((rates || DEFAULT_RATES)[code]));
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
