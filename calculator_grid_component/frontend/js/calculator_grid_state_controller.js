let calculatorState = null;
let activeCell = null;
let activeBackendRevision = null;
let activeDraftStorageKey = null;
let hasLocalDraft = false;
let backendSyncTimer = null;

function initializeState(payload) {
  const incomingDraftStorageKey = setCalculatorDraftStorageKey(payload.draft_storage_key);
  const incomingRevision = String(payload.state_revision || '');
  if (shouldKeepBrowserDraft(incomingRevision, incomingDraftStorageKey)) {
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
    numberOfPax: useStoredDraft ? storedDraft.numberOfPax ?? null : payload.number_of_pax ?? null,
    libraryRows: payload.library_rows || [],
    currencyRates: payload.currency_rates || DEFAULT_RATES,
    libraryStatus: payload.library_status || '',
    pendingDownload: payload.pending_download || null,
    showAdvanced: useStoredDraft ? Boolean(storedDraft.showAdvanced) : Boolean(payload.show_advanced),
    selectedRowIndex: useStoredDraft ? Number(storedDraft.selectedRowIndex || 0) : 0,
    activeSuggestion: null,
    validationErrors: [],
    dirty: Boolean(useStoredDraft),
    syncStatus: useStoredDraft ? 'Unsaved browser draft restored' : 'Saved',
    selection: useStoredDraft && storedDraft.selection ? {...storedDraft.selection} : null,
    columnWidths: useStoredDraft ? {...(storedDraft.columnWidths || {})} : {},
    showFindReplace: false,
    findQuery: '',
    replaceQuery: '',
    findMatchCursor: -1,
    undoStack: [],
    redoStack: []
  };
  activeCell = useStoredDraft && storedDraft.activeCell ? {...storedDraft.activeCell} : null;
  activeBackendRevision = incomingRevision;
  activeDraftStorageKey = incomingDraftStorageKey;
  hasLocalDraft = Boolean(useStoredDraft);
  validateCalculatorState(calculatorState);
  if (useStoredDraft) saveCalculatorDraft(calculatorState, activeBackendRevision);
}

function shouldKeepBrowserDraft(incomingRevision, incomingDraftStorageKey) {
  return Boolean(
    calculatorState
    && hasLocalDraft
    && incomingRevision
    && incomingRevision === activeBackendRevision
    && incomingDraftStorageKey
    && incomingDraftStorageKey === activeDraftStorageKey
  );
}

function mergeBackendPayloadWithoutRows(payload, incomingRevision) {
  calculatorState.libraryRows = payload.library_rows || calculatorState.libraryRows || [];
  calculatorState.currencyRates = payload.currency_rates || calculatorState.currencyRates || DEFAULT_RATES;
  calculatorState.libraryStatus = payload.library_status || calculatorState.libraryStatus || '';
  calculatorState.pendingDownload = payload.pending_download || null;
  calculatorState.numberOfPax = calculatorState.numberOfPax ?? payload.number_of_pax ?? null;
  activeBackendRevision = incomingRevision;
  activeDraftStorageKey = getCalculatorDraftStorageKey();
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  validateCalculatorState(calculatorState);
}

function markLocalDraft() {
  hasLocalDraft = true;
  calculatorState.dirty = true;
  calculatorState.syncStatus = 'Unsaved changes';
  validateCalculatorState(calculatorState);
  saveCalculatorDraft(calculatorState, activeBackendRevision);
  scheduleBackendSync();
  refreshSyncStatusOnly();
}

function scheduleBackendSync(delay = 650) {
  window.clearTimeout(backendSyncTimer);
  backendSyncTimer = window.setTimeout(() => submitAction('sync'), delay);
}

function flushBackendSync() {
  window.clearTimeout(backendSyncTimer);
  submitAction('sync');
}
