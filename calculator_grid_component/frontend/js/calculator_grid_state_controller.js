let calculatorState = null;
let activeCell = null;
let activeBackendRevision = null;
let activeDraftStorageKey = null;
let hasLocalDraft = false;
let localDraftSaveTimer = null;
let recoverySnapshotTimer = null;
const LOCAL_DRAFT_SAVE_DELAY_MS = 400;
const RECOVERY_SNAPSHOT_DELAY_MS = 2500;

function initializeState(payload) {
  const incomingDraftStorageKey = setCalculatorDraftStorageKey(payload.draft_storage_key);
  const incomingRevision = String(payload.state_revision || '');
  const ackOutcome = consumeCalculatorComponentAck(payload.component_ack, incomingRevision);
  if (ackOutcome.matched && ackOutcome.canRebaseNewerEdits && calculatorState) {
    mergeBackendPayloadWithoutRows(payload, incomingRevision);
    hasLocalDraft = true;
    calculatorState.dirty = true;
    calculatorState.syncStatus = 'Unsaved changes';
    saveCalculatorDraft(calculatorState, activeBackendRevision);
    return;
  }
  if (shouldKeepBrowserDraft(incomingRevision, incomingDraftStorageKey)) {
    mergeBackendPayloadWithoutRows(payload, incomingRevision);
    saveCalculatorDraft(calculatorState, activeBackendRevision);
    return;
  }

  const incomingRows = cloneRows(payload.rows || []).slice(0, MAX_CALCULATOR_ROWS);
  const libraryBundle = prepareLibraryBundle(
    payload.library_rows || [],
    payload.library_row_fields || [],
    payload.library_fingerprint || ''
  );
  const storedDraft = loadCalculatorDraft();
  const useStoredDraft = shouldRestoreCalculatorDraft(storedDraft, incomingRows, incomingRevision);
  const rows = calculateRows(useStoredDraft ? cloneRows(storedDraft.rows) : incomingRows, payload.currency_rates || DEFAULT_RATES);
  calculatorState = {
    rows: rows.length ? rows : addRows([], 25),
    numberOfPax: useStoredDraft ? storedDraft.numberOfPax ?? null : payload.number_of_pax ?? null,
    libraryRows: libraryBundle.rows,
    libraryIndex: libraryBundle.index,
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
    showVersionHistory: false,
    recoverySnapshots: loadCalculatorRecoverySnapshots(),
    recoveryWarning: calculatorStorageWarningMessage(),
    recoveryStorageBytes: calculatorRecoveryStorageUsage().totalBytes,
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
  calculatorState.recoverySnapshots = saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, useStoredDraft ? 'draft restored' : 'loaded');
  if (useStoredDraft) saveCalculatorDraft(calculatorState, activeBackendRevision);
  if (ackOutcome.matched && !ackOutcome.accepted) {
    calculatorState.syncStatus = ackOutcome.message || 'Older Calculator action was not applied';
  }
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
  const libraryBundle = prepareLibraryBundle(
    payload.library_rows || [],
    payload.library_row_fields || [],
    payload.library_fingerprint || ''
  );
  calculatorState.libraryRows = libraryBundle.rows;
  calculatorState.libraryIndex = libraryBundle.index;
  calculatorState.currencyRates = payload.currency_rates || calculatorState.currencyRates || DEFAULT_RATES;
  calculatorState.libraryStatus = payload.library_status || calculatorState.libraryStatus || '';
  // A same-revision backend render means the browser still owns newer, unsynced
  // edits. Any workbook prepared from the backend copy is therefore stale.
  calculatorState.pendingDownload = null;
  calculatorState.numberOfPax = calculatorState.numberOfPax ?? payload.number_of_pax ?? null;
  activeBackendRevision = incomingRevision;
  activeDraftStorageKey = getCalculatorDraftStorageKey();
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  validateCalculatorState(calculatorState);
}

function markLocalDraft(captureVersion = true, runValidation = true) {
  noteCalculatorLocalEdit();
  hasLocalDraft = true;
  calculatorState.dirty = true;
  calculatorState.pendingDownload = null;
  calculatorState.syncStatus = 'Unsaved changes';
  if (runValidation) validateCalculatorState(calculatorState);
  scheduleLocalDraftSave();
  if (captureVersion) scheduleRecoverySnapshot();
  refreshDownloadStateOnly();
  refreshSyncStatusOnly();
}

function scheduleLocalDraftSave(delay = LOCAL_DRAFT_SAVE_DELAY_MS) {
  window.clearTimeout(localDraftSaveTimer);
  localDraftSaveTimer = window.setTimeout(() => {
    localDraftSaveTimer = null;
    saveCalculatorDraft(calculatorState, activeBackendRevision);
  }, delay);
}

function flushLocalDraftSave() {
  window.clearTimeout(localDraftSaveTimer);
  localDraftSaveTimer = null;
  saveCalculatorDraft(calculatorState, activeBackendRevision);
}

function scheduleRecoverySnapshot(reason = 'edit', delay = RECOVERY_SNAPSHOT_DELAY_MS) {
  window.clearTimeout(recoverySnapshotTimer);
  recoverySnapshotTimer = window.setTimeout(() => {
    recoverySnapshotTimer = null;
    calculatorState.recoverySnapshots = saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, reason);
    refreshVersionHistoryCount();
  }, delay);
}

function flushRecoverySnapshot(reason = 'edit') {
  window.clearTimeout(recoverySnapshotTimer);
  recoverySnapshotTimer = null;
  calculatorState.recoverySnapshots = saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, reason);
  refreshVersionHistoryCount();
}
