// Calculator shell rendering orchestration.

function renderShell(state) {
  validateCalculatorState(state);
  const root = document.getElementById('root');
  root.innerHTML = `
    <div class="calculator-grid-shell${calculatorFullscreen ? ' fullscreen' : ''}" style="--sticky-col-1-left:${dynamicColumnWidth(columnByKey('row_id'), state.rows)}px">
      ${buildToolbarHtml(state)}
      ${buildFormulaBarHtml(state)}
      ${buildSalesPriceToolsHtml(state)}
      ${buildFindReplaceHtml(state)}
      ${buildVersionHistoryHtml(state)}
      <div id="calculator-dashboard-container">${dashboardTotalsHtml(state)}</div>
      <div id="calculator-validation-container">${validationSummaryHtml(state)}</div>
      ${buildTableHtml(state)}
      ${buildSuggestionHtml(state)}
    </div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

function refreshTotalsOnly() {
  const container = document.getElementById('calculator-dashboard-container');
  if (container) container.innerHTML = dashboardTotalsHtml(calculatorState);
}

function refreshFormulaBarOnly() {
  const input = document.querySelector('[data-action="formula-bar"]');
  const label = document.querySelector('.formula-reference');
  if (input) {
    input.disabled = !activeCell;
    if (document.activeElement !== input) input.value = activeCellRawValue();
  }
  if (label) {
    const column = activeCell ? columnByKey(activeCell.key) : null;
    const row = activeCell ? calculatorState.rows[activeCell.rowIndex] : null;
    label.textContent = column && row ? `${column.label} · row ${row.row_id || activeCell.rowIndex + 1}` : 'Select a cell';
  }
  refreshSalesPriceToolsOnly();
}

function refreshSalesPriceToolsOnly() {
  const tools = document.getElementById('sales-price-tools');
  if (!tools) return;
  tools.classList.toggle('hidden', !(activeCell && activeCell.key === 'sales_price_per_unit'));
}
