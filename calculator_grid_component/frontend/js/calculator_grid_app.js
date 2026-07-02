let calculatorState = null;
let activeCell = null;

function initializeState(payload) {
  const rows = calculateRows(cloneRows(payload.rows || []), payload.currency_rates || DEFAULT_RATES);
  calculatorState = {
    rows: rows.length ? rows : addRows([], 25),
    libraryRows: payload.library_rows || [],
    currencyRates: payload.currency_rates || DEFAULT_RATES,
    libraryStatus: payload.library_status || '',
    showAdvanced: Boolean(payload.show_advanced),
    selectedRowIndex: 0,
    activeSuggestion: null
  };
}

function rerender() {
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  renderShell(calculatorState);
  bindEvents();
}

function bindEvents() {
  document.querySelectorAll('[data-action="add"]').forEach((button) => {
    button.addEventListener('click', () => {
      calculatorState.rows = calculateRows(addRows(calculatorState.rows, Number(button.dataset.count || 1)), calculatorState.currencyRates);
      rerender();
    });
  });
  document.querySelector('[data-action="duplicate"]')?.addEventListener('click', () => {
    calculatorState.rows = calculateRows(duplicateRow(calculatorState.rows, calculatorState.selectedRowIndex), calculatorState.currencyRates);
    rerender();
  });
  document.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
    calculatorState.rows = calculateRows(deleteRow(calculatorState.rows, calculatorState.selectedRowIndex), calculatorState.currencyRates);
    calculatorState.selectedRowIndex = Math.min(calculatorState.selectedRowIndex, calculatorState.rows.length - 1);
    rerender();
  });
  document.querySelector('[data-action="toggle-advanced"]')?.addEventListener('change', (event) => {
    calculatorState.showAdvanced = Boolean(event.target.checked);
    rerender();
  });
  document.querySelector('[data-action="download"]')?.addEventListener('click', () => submitAction('download'));
  document.querySelector('[data-action="generate-agent"]')?.addEventListener('click', () => submitAction('generate_agent'));
  document.querySelector('[data-action="generate-customer"]')?.addEventListener('click', () => submitAction('generate_customer'));

  document.querySelectorAll('.calc-row').forEach((rowElement) => {
    rowElement.addEventListener('mousedown', () => {
      calculatorState.selectedRowIndex = Number(rowElement.dataset.rowIndex || 0);
      document.querySelectorAll('.calc-row').forEach((row) => row.classList.remove('selected-row'));
      rowElement.classList.add('selected-row');
    });
  });

  document.querySelectorAll('td.editable').forEach((cell) => {
    cell.addEventListener('focus', handleCellFocus);
    cell.addEventListener('input', handleCellInput);
    cell.addEventListener('keydown', handleCellKeydown);
    cell.addEventListener('blur', handleCellBlur);
  });
  document.querySelectorAll('td.checkbox-cell input').forEach((checkbox) => {
    checkbox.addEventListener('change', handleCheckboxChange);
  });
  document.querySelectorAll('.suggestion-item').forEach((button) => {
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      applySuggestion(Number(button.dataset.suggestionIndex || 0));
    });
  });
}

function handleCellFocus(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  calculatorState.selectedRowIndex = rowIndex;
  activeCell = {rowIndex, key};
  if (key === 'travel_element') updateSuggestions(rowIndex, cell.textContent || '');
  markSelectedRow(rowIndex);
}

function handleCellInput(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  updateRowValue(rowIndex, key, cell.textContent || '');
  refreshFormulaCells(rowIndex);
  refreshTotalsOnly();
  if (key === 'travel_element') {
    updateSuggestions(rowIndex, cell.textContent || '');
    renderSuggestionPanelOnly();
  }
}

function handleCellKeydown(event) {
  if (event.key === 'Enter') {
    event.preventDefault();
    event.currentTarget.blur();
  }
}

function handleCellBlur(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  if (['number', 'numberOptional', 'percent'].includes(columnKind(key))) {
    const value = row[key];
    cell.textContent = value === null || value === undefined || value === '' ? '' : String(value);
  }
}

function handleCheckboxChange(event) {
  const checkbox = event.currentTarget;
  const rowIndex = Number(checkbox.dataset.rowIndex || 0);
  const key = checkbox.dataset.key;
  updateRowValue(rowIndex, key, Boolean(checkbox.checked));
}

function columnKind(key) {
  const column = [...BASIC_COLUMNS, ...ADVANCED_COLUMNS, ...FORMULA_COLUMNS].find((item) => item.key === key);
  return column?.kind || 'text';
}

function updateRowValue(rowIndex, key, rawValue) {
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  const kind = columnKind(key);
  if (kind === 'checkbox') row[key] = Boolean(rawValue);
  else if (kind === 'numberOptional') row[key] = optionalNumberValue(rawValue);
  else if (kind === 'number' || kind === 'percent') row[key] = rawValue === '' ? '' : numberValue(rawValue);
  else row[key] = String(rawValue || '').trim();
  calculateRow(row, calculatorState.currencyRates);
}

function updateSuggestions(rowIndex, query) {
  const text = String(query || '').trim();
  if (text.length < 2) {
    calculatorState.activeSuggestion = null;
    return;
  }
  calculatorState.activeSuggestion = {
    rowIndex,
    query: text,
    results: findLibrarySuggestions(calculatorState.libraryRows, text, 8)
  };
}

function applySuggestion(index) {
  const active = calculatorState.activeSuggestion;
  if (!active || !active.results[index]) return;
  const row = calculatorState.rows[active.rowIndex];
  calculatorState.rows[active.rowIndex] = calculateRow(applyLibrarySuggestion(row, active.results[index].item), calculatorState.currencyRates);
  calculatorState.activeSuggestion = null;
  rerender();
}

function markSelectedRow(rowIndex) {
  document.querySelectorAll('.calc-row').forEach((row) => row.classList.remove('selected-row'));
  document.querySelector(`.calc-row[data-row-index="${rowIndex}"]`)?.classList.add('selected-row');
}

function refreshFormulaCells(rowIndex) {
  const row = calculatorState.rows[rowIndex];
  for (const column of FORMULA_COLUMNS) {
    const cell = document.querySelector(`td[data-row-index="${rowIndex}"][data-key="${column.key}"]`);
    if (cell) cell.textContent = formatFormula(row[column.key], column.kind);
  }
}

function refreshTotalsOnly() {
  const status = document.querySelector('.calculator-status-row');
  if (!status) return;
  const totals = calculateTotals(calculatorState.rows);
  status.innerHTML = `
    <span>${escapeHtml(calculatorState.libraryStatus || 'Local Library status unknown.')}</span>
    <span>Price: <strong>${formatNumber(totals.price, 0)}</strong></span>
    <span>Sales NOK: <strong>${formatNumber(totals.sales_price_nok_total, 0)}</strong></span>
    <span>GP NOK: <strong>${formatNumber(totals.gp_nok, 0)}</strong></span>
    <span>GP %: <strong>${(totals.gp_percent * 100).toFixed(1)}%</strong></span>`;
}

function renderSuggestionPanelOnly() {
  const oldPanel = document.querySelector('.suggestion-panel');
  if (oldPanel) oldPanel.remove();
  const html = buildSuggestionHtml(calculatorState);
  if (!html) return;
  document.querySelector('.calculator-grid-shell').insertAdjacentHTML('beforeend', html);
  document.querySelectorAll('.suggestion-item').forEach((button) => {
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      applySuggestion(Number(button.dataset.suggestionIndex || 0));
    });
  });
  requestAnimationFrame(setCalculatorFrameHeight);
}

function submitAction(action) {
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  Streamlit.setComponentValue(JSON.stringify({
    action,
    rows: normalizeRowsForPython(calculatorState.rows),
    show_advanced: calculatorState.showAdvanced
  }));
}

function renderError(error) {
  document.getElementById('root').innerHTML = `<div class="calculator-grid-shell"><div class="component-error"><strong>Calculator grid failed to render.</strong><br>${escapeHtml(error && error.message ? error.message : error)}</div></div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

window.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'streamlit:render') return;
  try {
    initializeState((event.data.args || {}).payload || {});
    rerender();
  } catch (error) {
    console.error(error);
    renderError(error);
  }
});
