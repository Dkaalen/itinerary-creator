// Sales-price command ownership.

function applySalesMargin(margin) {
  if (!activeCell || activeCell.key !== 'sales_price_per_unit') return;
  if (!(margin > 0 && margin < 1)) return;
  const rowIndex = activeCell.rowIndex;
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  const evaluator = new CalculatorGridFormulaEvaluator(calculatorState.rows, calculatorState.currencyRates);
  let salesPricePerUnit;
  try {
    salesPricePerUnit = evaluator.salesPricePerUnitForMargin(CALCULATOR_DATA_START_ROW + rowIndex, margin);
  } catch (_error) {
    salesPricePerUnit = 0;
  }
  if (!Number.isFinite(salesPricePerUnit) || salesPricePerUnit <= 0) {
    calculatorState.syncStatus = 'Enter a positive net cost, quantity and sales rate first';
    refreshSyncStatusOnly();
    return;
  }
  recordHistory();
  clearSalesPriceDerivedOverrides(row);
  row._sales_price_per_unit_touched = true;
  row.sales_price_per_unit = salesPricePerUnit;
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  markLocalDraft();
  rerender();
}

function useGrossAsSalesPrice() {
  if (!activeCell || activeCell.key !== 'sales_price_per_unit') return;
  const row = calculatorState.rows[activeCell.rowIndex];
  if (!row) return;
  recordHistory();
  clearSalesPriceDerivedOverrides(row);
  row._sales_price_per_unit_touched = false;
  row.sales_price_per_unit = null;
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  markLocalDraft();
  rerender();
}

function clearSalesPriceDerivedOverrides(row) {
  for (const field of activeFinancialRules.sales_price_derived_override_fields || []) row[field] = null;
}
