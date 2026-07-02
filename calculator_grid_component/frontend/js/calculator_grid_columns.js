const CALCULATOR_COLUMNS = [
  {key: 'row_id', label: 'ID', kind: 'text', width: 60},
  {key: 'day', label: 'Day', kind: 'text', width: 92},
  {key: 'type', label: 'Type', kind: 'text', width: 116},
  {key: 'from_date', label: 'From date', kind: 'text', width: 112},
  {key: 'to_date', label: 'To date', kind: 'text', width: 112},
  {key: 'from_time', label: 'From time', kind: 'text', width: 96},
  {key: 'to_time', label: 'To time', kind: 'text', width: 96},
  {key: 'supplier', label: 'Supplier', kind: 'text', width: 170},
  {key: 'travel_element', label: 'Travel element', kind: 'text', width: 360, autocomplete: true},
  {key: 'manual_booking', label: 'Manual booking?', kind: 'checkbox', width: 120},
  {key: 'status', label: 'Status', kind: 'text', width: 110},
  {key: 'comments', label: 'Comments', kind: 'text', width: 260},
  {key: 'non_refundable', label: 'Non-refundable', kind: 'checkbox', width: 120},
  {key: 'refundable', label: 'Refundable', kind: 'checkbox', width: 110},
  {key: 'url', label: 'URL', kind: 'url', width: 220},
  {key: 'gross_price_per_unit', label: 'Gross P per unit', kind: 'number', width: 130},
  {key: 'units', label: 'Units', kind: 'number', width: 80},
  {key: 'gross_price', label: 'Gross P', kind: 'formula', width: 110, formula: true},
  {key: 'supplier_commission', label: 'Supp Comm', kind: 'percent', width: 110},
  {key: 'net_price', label: 'Net P', kind: 'formula', width: 110, formula: true},
  {key: 'supplier_currency', label: 'Supp curr', kind: 'text', width: 92},
  {key: 'supplier_x_rate', label: 'X-rate', kind: 'formula', width: 92, formula: true},
  {key: 'net_price_nok', label: 'Net P NOK', kind: 'formula', width: 120, formula: true},
  {key: 'sales_price_per_unit', label: 'Sales P per unit', kind: 'numberOptional', width: 132},
  {key: 'price', label: 'Price', kind: 'formula', width: 110, formula: true},
  {key: 'sales_currency', label: 'Sales curr', kind: 'text', width: 92},
  {key: 'sales_x_rate', label: 'X-rate', kind: 'formula', width: 92, formula: true},
  {key: 'sales_price_nok_total', label: 'Sales P NOK tot', kind: 'formula', width: 140, formula: true},
  {key: 'gp_nok', label: 'GP NOK', kind: 'formula', width: 110, formula: true},
  {key: 'gp_percent', label: 'GP %', kind: 'formulaPercent', width: 92, formula: true},
  {key: 'vat25', label: 'VAT25', kind: 'number', width: 92},
  {key: 'vat15', label: 'VAT15', kind: 'number', width: 92},
  {key: 'vat12', label: 'VAT12', kind: 'number', width: 92},
  {key: 'vat0_domestic', label: 'VAT0-D', kind: 'number', width: 92},
  {key: 'vat0_international', label: 'VAT0-I', kind: 'number', width: 92}
];

const FORMULA_COLUMNS = CALCULATOR_COLUMNS.filter((column) => column.formula);
const ALL_EDITABLE_KEYS = new Set(CALCULATOR_COLUMNS.map((column) => column.key));
const FORMULA_OVERRIDE_KEYS = new Set(FORMULA_COLUMNS.map((column) => `${column.key}_override`));

function visibleColumns(_showAdvanced) {
  return CALCULATOR_COLUMNS;
}

function formulaOverrideKey(key) {
  return `${key}_override`;
}

function columnByKey(key) {
  return CALCULATOR_COLUMNS.find((column) => column.key === key);
}
