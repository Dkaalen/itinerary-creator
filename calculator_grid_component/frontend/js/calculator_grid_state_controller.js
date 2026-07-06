let calculatorState = null;
let activeCell = null;
let activeBackendRevision = null;
let hasLocalDraft = false;

function initializeState(payload) {
  const incomingRevision = String(payload.state_revision || '');
  if (shouldKeepBrowserDraft(incomingRevision)) {
    mergeBackendPayloadWithoutRows(payload, incomingRevision);
    saveCalculatorDraft(calculatorState, activeBackendRevision);
    return;
  }

  const incomingRows = cloneRows(payload.rows || []);
  const storedDraft = loadCalculatorDraft();
  const useStoredDraft = shouldRestoreCalculatorDraft(storedDraft, incomingRows, incomingRevision);
  const rows = calculateRows(useStoredDraft ? cloneRows(storedDraft.rows) : incomingRows, payload.currency_rates || DEFAULT_RATES);
  calculatorState = {
    rows: rows.length ? rows : addRows([], 25),
    libraryRows: payload.library_rows || [],
    currencyRates: payload.currency_rates || DEFAULT_RATES,
    libraryStatus: payload.library_status || '',
    showAdvanced: useStoredDraft ? Boolean(storedDraft.showAdvanced) : Boolean(payload.show_advanced),
    selectedRowIndex: useStoredDraft ? Number(storedDraft.selectedRowIndex || 0) : 0,
    activeSuggestion: null
  };
  activeBackendRevision = incomingRevision;
  hasLocalDraft = Boolean(useStoredDraft);
  if (useStoredDraft) saveCalculatorDraft(calculatorState, activeBackendRevision);
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
  saveCalculatorDraft(calculatorState, activeBackendRevision);
}
