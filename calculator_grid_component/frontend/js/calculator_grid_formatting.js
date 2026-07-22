// Number and formula display formatting.

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
