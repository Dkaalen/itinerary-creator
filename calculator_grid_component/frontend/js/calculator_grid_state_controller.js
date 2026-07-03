let calculatorState = null;
let activeCell = null;
let activeBackendRevision = null;
let hasLocalDraft = false;

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
