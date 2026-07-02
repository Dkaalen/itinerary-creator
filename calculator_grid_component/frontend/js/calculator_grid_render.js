function buildToolbarHtml(state) {
  const totals = calculateTotals(state.rows);
  const libraryText = state.libraryStatus || 'Local Library status unknown.';
  return `
    <div class="calculator-toolbar">
      <div class="calculator-toolbar-left">
        <button class="calc-btn" data-action="add" data-count="1">+1 row</button>
        <button class="calc-btn" data-action="add" data-count="5">+5 rows</button>
        <button class="calc-btn" data-action="add" data-count="10">+10 rows</button>
        <button class="calc-btn" data-action="duplicate">Duplicate row</button>
        <button class="calc-btn danger" data-action="delete">Delete row</button>
        <label class="advanced-toggle"><input type="checkbox" data-action="toggle-advanced" ${state.showAdvanced ? 'checked' : ''}> Show advanced columns</label>
      </div>
      <div class="calculator-toolbar-right">
        <button class="calc-btn primary" data-action="download">Prepare Excel download</button>
        <button class="calc-btn" data-action="generate-agent">Generate Agent Itinerary</button>
        <button class="calc-btn" data-action="generate-customer">Generate Customer Itinerary</button>
      </div>
    </div>
    <div class="calculator-status-row">
      <span>${escapeHtml(libraryText)}</span>
    </div>
    <div class="calculator-totals-panel">
      <span>Total price: <strong>${formatNumber(totals.price, 0)}</strong></span>
      <span>Total sales NOK: <strong>${formatNumber(totals.sales_price_nok_total, 0)}</strong></span>
      <span>Total net NOK: <strong>${formatNumber(totals.net_price_nok, 0)}</strong></span>
      <span>Earnings / GP NOK: <strong>${formatNumber(totals.gp_nok, 0)}</strong></span>
      <span>GP %: <strong>${(totals.gp_percent * 100).toFixed(1)}%</strong></span>
      <span>VAT25: <strong>${formatNumber(totals.vat25, 0)}</strong></span>
      <span>VAT15: <strong>${formatNumber(totals.vat15, 0)}</strong></span>
      <span>VAT12: <strong>${formatNumber(totals.vat12, 0)}</strong></span>
      <span>VAT0-D: <strong>${formatNumber(totals.vat0_domestic, 0)}</strong></span>
      <span>VAT0-I: <strong>${formatNumber(totals.vat0_international, 0)}</strong></span>
    </div>`;
}

function buildTableHtml(state) {
  const columns = visibleColumns(state.showAdvanced);
  const headers = columns.map((column) => `<th style="min-width:${column.width}px">${escapeHtml(column.label)}</th>`).join('');
  const body = state.rows.map((row, rowIndex) => {
    const selectedClass = rowIndex === state.selectedRowIndex ? ' selected-row' : '';
    const cells = columns.map((column) => cellHtml(row, rowIndex, column)).join('');
    return `<tr class="calc-row${selectedClass}" data-row-index="${rowIndex}">${cells}</tr>`;
  }).join('');
  return `
    <div class="calculator-grid-scroll">
      <table class="calculator-grid-table">
        <thead><tr>${headers}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function cellHtml(row, rowIndex, column) {
  const raw = row[column.key];
  const common = `data-row-index="${rowIndex}" data-key="${column.key}"`;
  if (column.formula) {
    return `<td class="cell editable formula-cell" contenteditable="true" spellcheck="false" ${common}>${escapeHtml(formatFormula(raw, column.kind))}</td>`;
  }
  if (column.kind === 'checkbox') {
    return `<td class="cell checkbox-cell" ${common}><input type="checkbox" ${raw ? 'checked' : ''} ${common}></td>`;
  }
  const value = raw === null || raw === undefined ? '' : String(raw);
  const autocompleteClass = column.autocomplete ? ' autocomplete-cell' : '';
  return `<td class="cell editable${autocompleteClass}" contenteditable="true" spellcheck="false" ${common}>${escapeHtml(value)}</td>`;
}

function buildSuggestionHtml(state) {
  if (!state.activeSuggestion) return '';
  const {rowIndex, query, results} = state.activeSuggestion;
  if (!results.length) {
    return `<div class="suggestion-panel"><div class="suggestion-empty">No Local Library matches for “${escapeHtml(query)}”.</div></div>`;
  }
  const buttons = results.map((result, index) => {
    const item = result.item;
    return `
      <button class="suggestion-item" data-suggestion-index="${index}">
        <strong>${escapeHtml(item.label || item.travel_element || item.library_id)}</strong>
        <span>${escapeHtml(item.preview || '')}</span>
      </button>`;
  }).join('');
  return `
    <div class="suggestion-panel">
      <div class="suggestion-title">Suggestions for row ${escapeHtml(state.rows[rowIndex]?.row_id || rowIndex + 1)}: “${escapeHtml(query)}”</div>
      ${buttons}
    </div>`;
}

function renderShell(state) {
  const root = document.getElementById('root');
  root.innerHTML = `
    <div class="calculator-grid-shell">
      <div class="calculator-grid-hint">Edit directly in the sheet. Use arrow keys, Enter, Tab, and Shift+Tab to move between cells. Travel element cells search the Local Library while you type. Formula cells update instantly but can be manually overridden.</div>
      ${buildToolbarHtml(state)}
      ${buildTableHtml(state)}
      ${buildSuggestionHtml(state)}
    </div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}
