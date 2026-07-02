const BASIC_COLUMNS = [
  {key: 'row_id', label: 'ID', kind: 'text', readonly: true, width: 60},
  {key: 'day', label: 'Day', kind: 'text', width: 100},
  {key: 'type', label: 'Type', kind: 'text', width: 120},
  {key: 'from_date', label: 'From date', kind: 'text', width: 120},
  {key: 'to_date', label: 'To date', kind: 'text', width: 120},
  {key: 'travel_element', label: 'Travel element', kind: 'text', width: 320, autocomplete: true},
  {key: 'url', label: 'URL', kind: 'url', width: 240},
  {key: 'gross_price_per_unit', label: 'Gross P per unit', kind: 'number', width: 130},
  {key: 'units', label: 'Units', kind: 'number', width: 86},
  {key: 'supplier_commission', label: 'Supp Comm %', kind: 'percent', width: 110},
  {key: 'supplier_currency', label: 'Supp curr', kind: 'text', width: 92},
  {key: 'sales_price_per_unit', label: 'Sales P per unit', kind: 'numberOptional', width: 130},
  {key: 'sales_currency', label: 'Sales curr', kind: 'text', width: 92}
];

const ADVANCED_COLUMNS = [
  {key: 'from_time', label: 'From time', kind: 'text', width: 100},
  {key: 'to_time', label: 'To time', kind: 'text', width: 100},
  {key: 'supplier', label: 'Supplier', kind: 'text', width: 180},
  {key: 'manual_booking', label: 'Manual booking?', kind: 'checkbox', width: 120},
  {key: 'status', label: 'Status', kind: 'text', width: 110},
  {key: 'comments', label: 'Comments', kind: 'text', width: 280},
  {key: 'non_refundable', label: 'Non-refundable', kind: 'checkbox', width: 120},
  {key: 'refundable', label: 'Refundable', kind: 'checkbox', width: 110},
  {key: 'vat25', label: 'VAT25', kind: 'number', width: 92},
  {key: 'vat15', label: 'VAT15', kind: 'number', width: 92},
  {key: 'vat12', label: 'VAT12', kind: 'number', width: 92},
  {key: 'vat0_domestic', label: 'VAT0-D', kind: 'number', width: 92},
  {key: 'vat0_international', label: 'VAT0-I', kind: 'number', width: 92}
];

const FORMULA_COLUMNS = [
  {key: 'gross_price', label: 'Gross P', kind: 'formula', width: 110},
  {key: 'net_price', label: 'Net P', kind: 'formula', width: 110},
  {key: 'supplier_x_rate', label: 'X-rate', kind: 'formula', width: 90},
  {key: 'net_price_nok', label: 'Net P NOK', kind: 'formula', width: 120},
  {key: 'calculated_sales_price_per_unit', label: 'Sales/unit calc', kind: 'formula', width: 130},
  {key: 'price', label: 'Price', kind: 'formula', width: 110},
  {key: 'sales_x_rate', label: 'Sales X-rate', kind: 'formula', width: 100},
  {key: 'sales_price_nok_total', label: 'Sales P NOK tot', kind: 'formula', width: 140},
  {key: 'gp_nok', label: 'GP NOK', kind: 'formula', width: 110},
  {key: 'gp_percent', label: 'GP %', kind: 'formulaPercent', width: 92}
];

const ALL_EDITABLE_KEYS = new Set([...BASIC_COLUMNS, ...ADVANCED_COLUMNS].map((column) => column.key));

function visibleColumns(showAdvanced) {
  return [...BASIC_COLUMNS, ...(showAdvanced ? ADVANCED_COLUMNS : []), ...FORMULA_COLUMNS];
}
