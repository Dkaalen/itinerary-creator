// Projection of one Local Library selection into an editable Calculator row.

(() => {
  'use strict';

  function applyLibrarySuggestion(row, suggestion) {
    const fetched = {...(suggestion.row_data || {})};
    const grossPerUnit = numberValue(fetched.gross_price_per_unit);
    const rawSalesPrice = fetched.sales_price_per_unit;
    const parsedSalesPrice = optionalNumberValue(rawSalesPrice);
    const hasExplicitSalesPrice = rawSalesPrice !== null
      && rawSalesPrice !== undefined
      && String(rawSalesPrice).trim() !== ''
      && !(parsedSalesPrice === 0 && grossPerUnit > 0);
    if (!hasExplicitSalesPrice) {
      fetched.sales_price_per_unit = '';
      fetched.sales_currency = row.sales_currency || DEFAULT_CURRENCY;
    }
    const preserved = {
      row_id: row.row_id,
      day: row.day || fetched.day || '',
      from_date: row.from_date || fetched.from_date || '',
      to_date: row.to_date || fetched.to_date || '',
      from_time: row.from_time || fetched.from_time || '',
      to_time: row.to_time || fetched.to_time || '',
    };
    return {
      ...fetched,
      ...preserved,
      _supplier_commission_touched: false,
      _sales_price_per_unit_touched: hasExplicitSalesPrice,
    };
  }

  window.ItineraryCalculator.define('library.selection', {
    applyLibrarySuggestion,
  });
})();
