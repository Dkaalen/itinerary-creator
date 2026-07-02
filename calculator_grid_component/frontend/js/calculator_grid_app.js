let calculatorState = null;
let activeCell = null;
let activeBackendRevision = null;
let hasLocalDraft = false;
let suggestionDebounceTimer = null;
let calculatorFullscreen = false;
const SUGGESTION_MIN_QUERY_LENGTH = 3;
const SUGGESTION_DEBOUNCE_MS = 180;

function initializeState(payload) {
  const incomingRevision = String(payload.state_revision || '');
  if (shouldKeepBrowserDraft(incomingRevision)) {
    mergeBackendPayloadWithoutRows(payload, incomingRevision);
    return;
  }

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
  activeBackendRevision = incomingRevision;
  hasLocalDraft = false;
}

function shouldKeepBrowserDraft(incomingRevision) {
  return Boolean(calculatorState && hasLocalDraft && incomingRevision && incomingRevision === activeBackendRevision);
}

function mergeBackendPayloadWithoutRows(payload, incomingRevision) {
  calculatorState.libraryRows = payload.library_rows || calculatorState.libraryRows || [];
  calculatorState.currencyRates = payload.currency_rates || calculatorState.currencyRates || DEFAULT_RATES;
  calculatorState.libraryStatus = payload.library_status || calculatorState.libraryStatus || '';
  activeBackendRevision = incomingRevision;
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
}

function markLocalDraft() {
  hasLocalDraft = true;
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
      markLocalDraft();
      rerender();
    });
  });
  document.querySelector('[data-action="duplicate"]')?.addEventListener('click', () => {
    calculatorState.rows = calculateRows(duplicateRow(calculatorState.rows, calculatorState.selectedRowIndex), calculatorState.currencyRates);
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
    calculatorState.rows = calculateRows(deleteRow(calculatorState.rows, calculatorState.selectedRowIndex), calculatorState.currencyRates);
    calculatorState.selectedRowIndex = Math.min(calculatorState.selectedRowIndex, calculatorState.rows.length - 1);
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="toggle-advanced"]')?.addEventListener('change', (event) => {
    calculatorState.showAdvanced = Boolean(event.target.checked);
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="download"]')?.addEventListener('click', () => submitAction('download'));
  document.querySelector('[data-action="generate-agent"]')?.addEventListener('click', () => submitAction('generate_agent'));
  document.querySelector('[data-action="generate-customer"]')?.addEventListener('click', () => submitAction('generate_customer'));
  document.querySelector('[data-action="toggle-fullscreen"]')?.addEventListener('click', toggleCalculatorFullscreen);

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
  if (key === 'travel_element') scheduleSuggestions(rowIndex, cell.textContent || '');
  markSelectedRow(rowIndex);
}

function handleCellInput(event) {
  const cell = event.currentTarget;
  const rowIndex = Number(cell.dataset.rowIndex || 0);
  const key = cell.dataset.key;
  updateRowValue(rowIndex, key, cell.textContent || '');
  markLocalDraft();
  if (key === 'day' || key === 'from_date') refreshDateCells();
  refreshDefaultedEditableCells(rowIndex);
  refreshFormulaCells(rowIndex);
  refreshTotalsOnly();
  if (key === 'travel_element') {
    scheduleSuggestions(rowIndex, cell.textContent || '');
  }
}

function handleCellKeydown(event) {
  const movement = navigationMovement(event);
  if (!movement) return;
  event.preventDefault();
  moveActiveCell(event.currentTarget, movement.rowDelta, movement.colDelta);
}

function navigationMovement(event) {
  if (event.key === 'ArrowRight') return {rowDelta: 0, colDelta: 1};
  if (event.key === 'ArrowLeft') return {rowDelta: 0, colDelta: -1};
  if (event.key === 'ArrowDown') return {rowDelta: 1, colDelta: 0};
  if (event.key === 'ArrowUp') return {rowDelta: -1, colDelta: 0};
  if (event.key === 'Tab') return {rowDelta: 0, colDelta: event.shiftKey ? -1 : 1};
  if (event.key === 'Enter') return {rowDelta: event.shiftKey ? -1 : 1, colDelta: 0};
  return null;
}

function moveActiveCell(cell, rowDelta, colDelta) {
  const columns = visibleColumns(calculatorState.showAdvanced);
  const currentRowIndex = Number(cell.dataset.rowIndex || 0);
  const currentKey = cell.dataset.key;
  const currentColIndex = columns.findIndex((column) => column.key === currentKey);
  if (currentColIndex < 0) return;
  const targetRowIndex = Math.max(0, Math.min(calculatorState.rows.length - 1, currentRowIndex + rowDelta));
  const targetColIndex = Math.max(0, Math.min(columns.length - 1, currentColIndex + colDelta));
  const targetKey = columns[targetColIndex].key;
  const target = document.querySelector(`[data-row-index="${targetRowIndex}"][data-key="${targetKey}"]`);
  if (!target) return;
  const input = target.matches('input') ? target : target.querySelector?.('input');
  if (input) {
    input.focus();
    return;
  }
  target.focus();
  selectCellText(target);
}

function selectCellText(cell) {
  const range = document.createRange();
  range.selectNodeContents(cell);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
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
  } else if (['formula', 'formulaPercent'].includes(columnKind(key))) {
    cell.textContent = formatFormula(row[key], columnKind(key));
  } else if (key === 'supplier_currency' || key === 'sales_currency') {
    cell.textContent = row[key] || '';
  }
}

function handleCheckboxChange(event) {
  const checkbox = event.currentTarget;
  const rowIndex = Number(checkbox.dataset.rowIndex || 0);
  const key = checkbox.dataset.key;
  updateRowValue(rowIndex, key, Boolean(checkbox.checked));
  markLocalDraft();
}

function columnKind(key) {
  const column = columnByKey(key);
  return column?.kind || 'text';
}

function updateRowValue(rowIndex, key, rawValue) {
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  const kind = columnKind(key);
  if (key === 'supplier_commission') row._supplier_commission_touched = true;
  if (key === 'units') row._units_touched = true;
  if (key === 'sales_price_per_unit') row._sales_price_per_unit_touched = true;
  if (kind === 'checkbox') row[key] = Boolean(rawValue);
  else if (kind === 'numberOptional') row[key] = optionalNumberValue(rawValue);
  else if (kind === 'formula' || kind === 'formulaPercent') {
    row[formulaOverrideKey(key)] = formulaOverrideValue(rawValue, kind);
  } else if (kind === 'percent') row[key] = rawValue === '' ? '' : percentPointInputValue(rawValue);
  else if (kind === 'number') row[key] = rawValue === '' ? '' : numberValue(rawValue);
  else row[key] = normalizedTextValue(key, rawValue);
  if (key === 'day' || key === 'from_date') autofillDatesFromArrival(calculatorState.rows);
  calculateRow(row, calculatorState.currencyRates);
}

function normalizedTextValue(key, rawValue) {
  const text = String(rawValue || '').trim();
  if (key === 'supplier_currency' || key === 'sales_currency') return text.toUpperCase();
  return text;
}

function formulaOverrideValue(rawValue, kind) {
  if (rawValue === null || rawValue === undefined || String(rawValue).trim() === '') return null;
  if (kind === 'formulaPercent') return percentInputValue(rawValue);
  return numberValue(rawValue);
}

function percentInputValue(rawValue) {
  const text = String(rawValue || '').trim();
  const number = numberValue(rawValue);
  return text.includes('%') ? number : number / 100;
}

function percentPointInputValue(rawValue) {
  const text = String(rawValue || '').trim();
  const number = numberValue(rawValue);
  return text.includes('%') ? number * 100 : number;
}

function scheduleSuggestions(rowIndex, query) {
  window.clearTimeout(suggestionDebounceTimer);
  const text = String(query || '').trim();
  if (text.length < SUGGESTION_MIN_QUERY_LENGTH) {
    calculatorState.activeSuggestion = null;
    renderSuggestionPanelOnly();
    return;
  }
  suggestionDebounceTimer = window.setTimeout(() => {
    if (!activeCell || activeCell.rowIndex !== rowIndex || activeCell.key !== 'travel_element') return;
    const focused = document.activeElement;
    if (!focused || focused.dataset?.rowIndex !== String(rowIndex) || focused.dataset?.key !== 'travel_element') return;
    updateSuggestions(rowIndex, focused.textContent || text);
    renderSuggestionPanelOnly();
  }, SUGGESTION_DEBOUNCE_MS);
}

function updateSuggestions(rowIndex, query) {
  const text = String(query || '').trim();
  if (text.length < SUGGESTION_MIN_QUERY_LENGTH) {
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
  calculatorState.rows[active.rowIndex] = applyLibrarySuggestion(row, active.results[index].item);
  autofillDatesFromArrival(calculatorState.rows);
  calculatorState.rows[active.rowIndex] = calculateRow(calculatorState.rows[active.rowIndex], calculatorState.currencyRates);
  calculatorState.activeSuggestion = null;
  markLocalDraft();
  rerender();
}

function markSelectedRow(rowIndex) {
  document.querySelectorAll('.calc-row').forEach((row) => row.classList.remove('selected-row'));
  document.querySelector(`.calc-row[data-row-index="${rowIndex}"]`)?.classList.add('selected-row');
}


function refreshDateCells() {
  for (let index = 0; index < calculatorState.rows.length; index += 1) {
    const cell = document.querySelector(`td[data-row-index="${index}"][data-key="from_date"]`);
    if (!cell || document.activeElement === cell) continue;
    cell.textContent = calculatorState.rows[index].from_date || '';
  }
}

function refreshDefaultedEditableCells(rowIndex) {
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  for (const key of ['units', 'supplier_commission', 'sales_price_per_unit']) {
    const cell = document.querySelector(`td[data-row-index="${rowIndex}"][data-key="${key}"]`);
    if (!cell || document.activeElement === cell) continue;
    const value = row[key];
    cell.textContent = value === null || value === undefined || value === '' ? '' : String(value);
  }
}

function refreshFormulaCells(rowIndex) {
  const row = calculatorState.rows[rowIndex];
  for (const column of FORMULA_COLUMNS) {
    const cell = document.querySelector(`td[data-row-index="${rowIndex}"][data-key="${column.key}"]`);
    if (cell && !(activeCell && activeCell.rowIndex === rowIndex && activeCell.key === column.key && document.activeElement === cell)) {
      cell.textContent = formatFormula(row[column.key], column.kind);
    }
  }
}

function refreshTotalsOnly() {
  const totalsPanel = document.querySelector('.calculator-totals-panel');
  if (!totalsPanel) return;
  const totals = calculateTotals(calculatorState.rows);
  totalsPanel.innerHTML = `
    <span>Total price: <strong>${formatNumber(totals.price, 0)}</strong></span>
    <span>Total sales NOK: <strong>${formatNumber(totals.sales_price_nok_total, 0)}</strong></span>
    <span>Total net NOK: <strong>${formatNumber(totals.net_price_nok, 0)}</strong></span>
    <span>Earnings / GP NOK: <strong>${formatNumber(totals.gp_nok, 0)}</strong></span>
    <span>GP %: <strong>${(totals.gp_percent * 100).toFixed(1)}%</strong></span>
    <span>VAT25: <strong>${formatNumber(totals.vat25, 0)}</strong></span>
    <span>VAT15: <strong>${formatNumber(totals.vat15, 0)}</strong></span>
    <span>VAT12: <strong>${formatNumber(totals.vat12, 0)}</strong></span>
    <span>VAT0-D: <strong>${formatNumber(totals.vat0_domestic, 0)}</strong></span>
    <span>VAT0-I: <strong>${formatNumber(totals.vat0_international, 0)}</strong></span>`;
}

function toggleCalculatorFullscreen() {
  calculatorFullscreen = !calculatorFullscreen;
  const shell = document.querySelector('.calculator-grid-shell');
  if (!shell) return;
  shell.classList.toggle('fullscreen', calculatorFullscreen);
  setCalculatorHostFullscreen(calculatorFullscreen);
  updateFullscreenButton();
  if (calculatorFullscreen && shell.requestFullscreen && !document.fullscreenElement) {
    shell.requestFullscreen().catch(() => {
      // Browser or iframe refused native fullscreen; keep the host iframe fullscreen fallback active.
    });
  } else if (!calculatorFullscreen && document.fullscreenElement && document.exitFullscreen) {
    document.exitFullscreen().catch(() => {});
  }
  requestAnimationFrame(setCalculatorFrameHeight);
}

function updateFullscreenButton() {
  const button = document.querySelector('[data-action="toggle-fullscreen"]');
  if (button) button.textContent = calculatorFullscreen ? 'Exit fullscreen' : 'Fullscreen calculator';
}

function handleFullscreenChange() {
  if (!document.fullscreenElement && calculatorFullscreen) {
    calculatorFullscreen = false;
    document.querySelector('.calculator-grid-shell')?.classList.remove('fullscreen');
    setCalculatorHostFullscreen(false);
    updateFullscreenButton();
    requestAnimationFrame(setCalculatorFrameHeight);
  }
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
}


function submitAction(action) {
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  const rows = normalizeRowsForPython(calculatorState.rows);
  Streamlit.setComponentValue(JSON.stringify({
    action,
    rows,
    show_advanced: calculatorState.showAdvanced,
    client_state_revision: activeBackendRevision
  }));
}

function renderError(error) {
  document.getElementById('root').innerHTML = `<div class="calculator-grid-shell"><div class="component-error"><strong>Calculator grid failed to render.</strong><br>${escapeHtml(error && error.message ? error.message : error)}</div></div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

let componentHasReceivedRender = false;

function handleStreamlitRender(event) {
  if (!event.data || event.data.type !== 'streamlit:render') return;
  componentHasReceivedRender = true;
  try {
    initializeState((event.data.args || {}).payload || {});
    rerender();
  } catch (error) {
    console.error(error);
    renderError(error);
  }
}

function startCalculatorGridComponent() {
  renderComponentBootMessage('Loading calculator grid…');
  window.addEventListener('message', handleStreamlitRender);
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  Streamlit.setComponentReady();
  requestAnimationFrame(setCalculatorFrameHeight);
  window.setTimeout(() => {
    if (!componentHasReceivedRender) {
      renderComponentBootMessage('Waiting for calculator data from Streamlit…');
    }
  }, 2000);
}

startCalculatorGridComponent();
