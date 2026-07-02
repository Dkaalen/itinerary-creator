const CALCULATOR_COLUMNS = [
  {key: 'row_id', label: 'ID', kind: 'text', minWidth: 44, maxWidth: 56, fitChars: 3},
  {key: 'day', label: 'Day', kind: 'text', minWidth: 58, maxWidth: 78, fitChars: 7},
  {key: 'type', label: 'Type', kind: 'text', minWidth: 76, maxWidth: 120, fitChars: 12},
  {key: 'from_date', label: 'From date', kind: 'text', minWidth: 92, maxWidth: 104, fitChars: 10},
  {key: 'to_date', label: 'To date', kind: 'text', minWidth: 80, maxWidth: 100, fitChars: 10},
  {key: 'from_time', label: 'From time', kind: 'text', minWidth: 86, maxWidth: 94, fitChars: 8, advanced: true},
  {key: 'to_time', label: 'To time', kind: 'text', minWidth: 76, maxWidth: 90, fitChars: 8, advanced: true},
  {key: 'supplier', label: 'Supplier', kind: 'text', minWidth: 110, maxWidth: 170, fitChars: 18, advanced: true},
  {key: 'travel_element', label: 'Travel element', kind: 'text', minWidth: 320, maxWidth: 560, fitChars: 72, autocomplete: true},
  {key: 'manual_booking', label: 'Manual booking?', kind: 'checkbox', minWidth: 120, maxWidth: 132, fitChars: 5, advanced: true},
  {key: 'status', label: 'Status', kind: 'text', minWidth: 74, maxWidth: 110, fitChars: 10, advanced: true},
  {key: 'comments', label: 'Comments', kind: 'text', minWidth: 150, maxWidth: 260, fitChars: 32, advanced: true},
  {key: 'non_refundable', label: 'Non-refundable', kind: 'checkbox', minWidth: 120, maxWidth: 130, fitChars: 5, advanced: true},
  {key: 'refundable', label: 'Refundable', kind: 'checkbox', minWidth: 100, maxWidth: 112, fitChars: 5, advanced: true},
  {key: 'url', label: 'URL', kind: 'url', minWidth: 120, maxWidth: 210, fitChars: 28, advanced: true},
  {key: 'gross_price_per_unit', label: 'Gross P per unit', kind: 'number', minWidth: 122, maxWidth: 138, fitChars: 11},
  {key: 'units', label: 'Units', kind: 'number', minWidth: 58, maxWidth: 70, fitChars: 5},
  {key: 'gross_price', label: 'Gross P', kind: 'formula', minWidth: 82, maxWidth: 118, fitChars: 12, formula: true},
  {key: 'supplier_commission', label: 'Supp Comm', kind: 'percent', minWidth: 82, maxWidth: 94, fitChars: 7},
  {key: 'net_price', label: 'Net P', kind: 'formula', minWidth: 76, maxWidth: 118, fitChars: 12, formula: true},
  {key: 'supplier_currency', label: 'Supp curr', kind: 'text', minWidth: 78, maxWidth: 90, fitChars: 5},
  {key: 'supplier_x_rate', label: 'X-rate', kind: 'formula', minWidth: 66, maxWidth: 86, fitChars: 7, formula: true},
  {key: 'net_price_nok', label: 'Net P NOK', kind: 'formula', minWidth: 98, maxWidth: 138, fitChars: 13, formula: true},
  {key: 'sales_price_per_unit', label: 'Sales P per unit', kind: 'numberOptional', minWidth: 122, maxWidth: 148, fitChars: 12},
  {key: 'price', label: 'Price', kind: 'formula', minWidth: 88, maxWidth: 132, fitChars: 13, formula: true},
  {key: 'sales_currency', label: 'Sales curr', kind: 'text', minWidth: 78, maxWidth: 90, fitChars: 5},
  {key: 'sales_x_rate', label: 'X-rate', kind: 'formula', minWidth: 66, maxWidth: 86, fitChars: 7, formula: true},
  {key: 'sales_price_nok_total', label: 'Sales P NOK tot', kind: 'formula', minWidth: 128, maxWidth: 158, fitChars: 13, formula: true},
  {key: 'gp_nok', label: 'GP NOK', kind: 'formula', minWidth: 88, maxWidth: 126, fitChars: 12, formula: true},
  {key: 'gp_percent', label: 'GP %', kind: 'formulaPercent', minWidth: 72, maxWidth: 92, fitChars: 8, formula: true},
  {key: 'vat25', label: 'VAT25', kind: 'number', minWidth: 62, maxWidth: 80, fitChars: 8, advanced: true},
  {key: 'vat15', label: 'VAT15', kind: 'number', minWidth: 62, maxWidth: 80, fitChars: 8, advanced: true},
  {key: 'vat12', label: 'VAT12', kind: 'number', minWidth: 62, maxWidth: 80, fitChars: 8, advanced: true},
  {key: 'vat0_domestic', label: 'VAT0-D', kind: 'number', minWidth: 70, maxWidth: 86, fitChars: 8, advanced: true},
  {key: 'vat0_international', label: 'VAT0-I', kind: 'number', minWidth: 70, maxWidth: 86, fitChars: 8, advanced: true}
];

const FORMULA_COLUMNS = CALCULATOR_COLUMNS.filter((column) => column.formula);
const ALL_EDITABLE_KEYS = new Set(CALCULATOR_COLUMNS.map((column) => column.key));
const FORMULA_OVERRIDE_KEYS = new Set(FORMULA_COLUMNS.map((column) => `${column.key}_override`));
const ADVANCED_COLUMN_KEYS = new Set(CALCULATOR_COLUMNS.filter((column) => column.advanced).map((column) => column.key));

function visibleColumns(showAdvanced) {
  return CALCULATOR_COLUMNS.filter((column) => showAdvanced || !column.advanced);
}

function formulaOverrideKey(key) {
  return `${key}_override`;
}

function columnByKey(key) {
  return CALCULATOR_COLUMNS.find((column) => column.key === key);
}
