let calculatorState = null;
let activeCell = null;
let activeBackendRevision = null;
let activeDraftStorageKey = null;
let activeProjectIdentity = null;
let hasLocalDraft = false;
let localDraftSaveTimer = null;
let recoverySnapshotTimer = null;
let recoveryBaselineState = null;
const LOCAL_DRAFT_SAVE_DELAY_MS = 400;
const RECOVERY_SNAPSHOT_DELAY_MS = 2500;

async function initializeState(payload) {
  await window.ItineraryCalculator.storage.initializeStorage(payload.browser_storage_contract, payload.draft_storage_key);
  setActiveFinancialRules(payload.financial_rules || DEFAULT_FINANCIAL_RULES);
  const incomingDraftStorageKey = window.ItineraryCalculator.storage.setDraftStorageKey(payload.draft_storage_key);
  const incomingProjectIdentity = String(payload.project_identity || "");
  const incomingRevision = String(payload.state_revision || '');
  const ackOutcome = consumeCalculatorComponentAck(payload.component_ack, incomingRevision);
  if (ackOutcome.matched && ackOutcome.canRebaseNewerEdits && calculatorState) {
    mergeBackendPayloadWithoutRows(payload, incomingRevision);
    hasLocalDraft = true;
    calculatorState.dirty = true;
    calculatorState.syncStatus = 'Unsaved changes';
    window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
    return;
  }
  if (shouldKeepBrowserDraft(incomingRevision, incomingDraftStorageKey)) {
    mergeBackendPayloadWithoutRows(payload, incomingRevision);
    window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
    return;
  }

  const incomingRows = cloneRows(payload.rows || []).slice(0, MAX_CALCULATOR_ROWS);
  const libraryBundle = window.ItineraryCalculator.library.prepareBundle(payload);
  const storedDraft = window.ItineraryCalculator.storage.loadDraft();
  const useStoredDraft = window.ItineraryCalculator.storage.shouldRestoreDraft(storedDraft, incomingRows, incomingRevision);
  const rows = calculateRows(useStoredDraft ? cloneRows(storedDraft.rows) : incomingRows, payload.currency_rates || DEFAULT_RATES);
  calculatorState = {
    rows: rows.length ? rows : addRows([], 25),
    numberOfPax: useStoredDraft ? storedDraft.numberOfPax ?? null : payload.number_of_pax ?? null,
    libraryRows: libraryBundle.rows,
    libraryIndex: libraryBundle.index,
    libraryRankingSpec: payload.library_ranking_spec || {},
    currencyRates: payload.currency_rates || DEFAULT_RATES,
    libraryStatus: payload.library_status || '',
    pendingDownload: payload.pending_download || null,
    showAdvanced: useStoredDraft ? Boolean(storedDraft.showAdvanced) : Boolean(payload.show_advanced),
    selectedRowIndex: useStoredDraft ? Number(storedDraft.selectedRowIndex || 0) : 0,
    activeSuggestion: null,
    validationErrors: [],
    dirty: Boolean(useStoredDraft),
    syncStatus: useStoredDraft ? 'Local changes restored' : 'Workspace synced',
    selection: useStoredDraft && storedDraft.selection ? {...storedDraft.selection} : null,
    columnWidths: useStoredDraft ? {...(storedDraft.columnWidths || {})} : {},
    showFindReplace: false,
    showVersionHistory: false,
    recoverySnapshots: window.ItineraryCalculator.storage.loadRecoverySnapshots(),
    recoveryStatus: window.ItineraryCalculator.storage.statusPayload(),
    recoveryWarning: window.ItineraryCalculator.storage.warningMessage(),
    recoveryStorageBytes: window.ItineraryCalculator.storage.storageUsage().totalBytes,
    findQuery: '',
    replaceQuery: '',
    findMatchCursor: -1,
    undoStack: [],
    redoStack: []
  };
  activeCell = useStoredDraft && storedDraft.activeCell ? {...storedDraft.activeCell} : null;
  recoveryBaselineState = (calculatorState.recoverySnapshots || []).length ? null : {
    rows: cloneRows(calculatorState.rows),
    numberOfPax: calculatorState.numberOfPax ?? null,
    showAdvanced: Boolean(calculatorState.showAdvanced),
    selectedRowIndex: Number(calculatorState.selectedRowIndex || 0),
    selection: calculatorState.selection ? {...calculatorState.selection} : null,
    columnWidths: {...(calculatorState.columnWidths || {})},
    recoveryActiveCell: activeCell ? {...activeCell} : null,
  };
  activeBackendRevision = incomingRevision;
  activeDraftStorageKey = incomingDraftStorageKey;
  activeProjectIdentity = incomingProjectIdentity;
  hasLocalDraft = Boolean(useStoredDraft);
  validateCalculatorState(calculatorState);
  if (useStoredDraft) window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
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
  setActiveFinancialRules(payload.financial_rules || activeFinancialRules || DEFAULT_FINANCIAL_RULES);
  const libraryBundle = window.ItineraryCalculator.library.prepareBundle({
    ...payload,
    library_ranking_spec: payload.library_ranking_spec || calculatorState.libraryRankingSpec || {},
  });
  calculatorState.libraryRows = libraryBundle.rows;
  calculatorState.libraryIndex = libraryBundle.index;
  calculatorState.libraryRankingSpec = payload.library_ranking_spec || calculatorState.libraryRankingSpec || {};
  calculatorState.currencyRates = payload.currency_rates || calculatorState.currencyRates || DEFAULT_RATES;
  calculatorState.libraryStatus = payload.library_status || calculatorState.libraryStatus || '';
  // A same-revision backend render means the browser still owns newer, unsynced
  // edits. Any workbook prepared from the backend copy is therefore stale.
  calculatorState.pendingDownload = null;
  calculatorState.numberOfPax = calculatorState.numberOfPax ?? payload.number_of_pax ?? null;
  activeBackendRevision = incomingRevision;
  activeDraftStorageKey = window.ItineraryCalculator.storage.getDraftStorageKey();
  activeProjectIdentity = String(payload.project_identity || activeProjectIdentity || "");
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  validateCalculatorState(calculatorState);
}

function markLocalDraft(captureVersion = true, runValidation = true) {
  if (recoveryBaselineState) {
    calculatorState.recoverySnapshots = window.ItineraryCalculator.storage.saveRecoverySnapshot(
      recoveryBaselineState,
      activeBackendRevision,
      'baseline'
    );
    recoveryBaselineState = null;
    refreshVersionHistoryCount();
  }
  noteCalculatorLocalEdit();
  window.ItineraryCalculator.storage.resumeLocalRecovery();
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
    window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
  }, delay);
}

function flushLocalDraftSave() {
  window.clearTimeout(localDraftSaveTimer);
  localDraftSaveTimer = null;
  if (!calculatorState?.dirty && !hasLocalDraft) return;
  window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
}

function scheduleRecoverySnapshot(reason = 'edit', delay = RECOVERY_SNAPSHOT_DELAY_MS) {
  window.clearTimeout(recoverySnapshotTimer);
  recoverySnapshotTimer = window.setTimeout(() => {
    recoverySnapshotTimer = null;
    calculatorState.recoverySnapshots = window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, reason);
    refreshVersionHistoryCount();
  }, delay);
}

function flushRecoverySnapshot(reason = 'edit') {
  window.clearTimeout(recoverySnapshotTimer);
  recoverySnapshotTimer = null;
  if (!calculatorState?.dirty) return;
  calculatorState.recoverySnapshots = window.ItineraryCalculator.storage.saveRecoverySnapshot(calculatorState, activeBackendRevision, reason);
  refreshVersionHistoryCount();
}
