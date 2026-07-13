let calculatorDraftStorageKey = 'itineraryCalculatorBrowserDraft.v3.global';
const CALCULATOR_DRAFT_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 30;

function setCalculatorDraftStorageKey(key) {
  const value = String(key || '').trim();
  calculatorDraftStorageKey = value || 'itineraryCalculatorBrowserDraft.v3.global';
  return calculatorDraftStorageKey;
}

function getCalculatorDraftStorageKey() {
  return calculatorDraftStorageKey;
}

function loadCalculatorDraft() {
  try {
    const raw = window.localStorage.getItem(calculatorDraftStorageKey);
    if (!raw) return null;
    const draft = JSON.parse(raw);
    if (!draft || !Array.isArray(draft.rows)) return null;
    if (Date.now() - Number(draft.savedAt || 0) > CALCULATOR_DRAFT_MAX_AGE_MS) {
      clearCalculatorDraft();
      return null;
    }
    return draft;
  } catch (_error) {
    return null;
  }
}

function saveCalculatorDraft(state, backendRevision) {
  if (!state || !Array.isArray(state.rows)) return;
  try {
    window.localStorage.setItem(calculatorDraftStorageKey, JSON.stringify({
      rows: normalizeRowsForPython(state.rows),
      numberOfPax: state.numberOfPax ?? null,
      showAdvanced: Boolean(state.showAdvanced),
      selectedRowIndex: Number(state.selectedRowIndex || 0),
      activeCell: activeCell ? {...activeCell} : null,
      selection: state.selection ? {...state.selection} : null,
      columnWidths: {...(state.columnWidths || {})},
      backendRevision: String(backendRevision || ''),
      savedAt: Date.now()
    }));
  } catch (_error) {
    // localStorage can be unavailable in private mode. The grid should still work.
  }
}

function clearCalculatorDraft() {
  try {
    window.localStorage.removeItem(calculatorDraftStorageKey);
  } catch (_error) {
    // No-op.
  }
}

function shouldRestoreCalculatorDraft(draft, incomingRows, incomingRevision) {
  if (!draft || !Array.isArray(draft.rows) || !draft.rows.length) return false;
  const draftRevision = String(draft.backendRevision || '');
  const revisionsMatch = Boolean(draftRevision && incomingRevision && draftRevision === String(incomingRevision));
  if (!Array.isArray(incomingRows) || !incomingRows.length) return revisionsMatch || !incomingRevision;
  if (gridRowsAreBlank(incomingRows)) return revisionsMatch;
  return revisionsMatch;
}

function gridRowsAreBlank(rows) {
  return (rows || []).every((row) => !rowHasUserContent(row));
}


function rowHasUserContent(row) {
  const ignored = new Set(['row_id', 'supplier_currency', 'sales_currency']);
  for (const [key, value] of Object.entries(row || {})) {
    if (ignored.has(key) || key.endsWith('_override')) continue;
    if (typeof value === 'boolean') {
      if (value) return true;
      continue;
    }
    if (value === null || value === undefined) continue;
    if (String(value).trim() !== '' && String(value).trim() !== '0') return true;
  }
  return false;
}

const CALCULATOR_RECOVERY_MAX_SNAPSHOTS = 20;

function calculatorRecoveryStorageKey() {
  return `${calculatorDraftStorageKey}.versions`;
}

function loadCalculatorRecoverySnapshots() {
  try {
    const raw = window.localStorage.getItem(calculatorRecoveryStorageKey());
    if (!raw) return [];
    const snapshots = JSON.parse(raw);
    if (!Array.isArray(snapshots)) return [];
    const cutoff = Date.now() - CALCULATOR_DRAFT_MAX_AGE_MS;
    return snapshots
      .filter((snapshot) => snapshot && Array.isArray(snapshot.rows) && Number(snapshot.savedAt || 0) >= cutoff)
      .slice(0, CALCULATOR_RECOVERY_MAX_SNAPSHOTS);
  } catch (_error) {
    return [];
  }
}

function calculatorRecoverySignature(state) {
  return JSON.stringify({
    rows: normalizeRowsForPython(state.rows),
    numberOfPax: state.numberOfPax ?? null,
    showAdvanced: Boolean(state.showAdvanced),
    columnWidths: {...(state.columnWidths || {})}
  });
}

function saveCalculatorRecoverySnapshot(state, backendRevision, reason = 'edit') {
  if (!state || !Array.isArray(state.rows)) return [];
  try {
    const snapshots = loadCalculatorRecoverySnapshots();
    const signature = calculatorRecoverySignature(state);
    if (snapshots[0]?.signature === signature) return snapshots;
    const snapshot = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      rows: normalizeRowsForPython(state.rows),
      numberOfPax: state.numberOfPax ?? null,
      showAdvanced: Boolean(state.showAdvanced),
      selectedRowIndex: Number(state.selectedRowIndex || 0),
      activeCell: activeCell ? {...activeCell} : null,
      selection: state.selection ? {...state.selection} : null,
      columnWidths: {...(state.columnWidths || {})},
      backendRevision: String(backendRevision || ''),
      savedAt: Date.now(),
      reason: String(reason || 'edit'),
      signature
    };
    const updated = [snapshot, ...snapshots].slice(0, CALCULATOR_RECOVERY_MAX_SNAPSHOTS);
    window.localStorage.setItem(calculatorRecoveryStorageKey(), JSON.stringify(updated));
    return updated;
  } catch (_error) {
    return [];
  }
}

function restoreCalculatorRecoverySnapshot(snapshotId) {
  const snapshot = loadCalculatorRecoverySnapshots().find((item) => item.id === snapshotId);
  if (!snapshot || !calculatorState) return false;
  recordHistory();
  calculatorState.rows = calculateRows(cloneRows(snapshot.rows), calculatorState.currencyRates);
  calculatorState.numberOfPax = snapshot.numberOfPax ?? null;
  calculatorState.showAdvanced = Boolean(snapshot.showAdvanced);
  calculatorState.selectedRowIndex = Number(snapshot.selectedRowIndex || 0);
  calculatorState.selection = snapshot.selection ? {...snapshot.selection} : null;
  calculatorState.columnWidths = {...(snapshot.columnWidths || {})};
  activeCell = snapshot.activeCell ? {...snapshot.activeCell} : null;
  calculatorState.dirty = true;
  calculatorState.syncStatus = `Recovered version from ${new Date(snapshot.savedAt).toLocaleString()}`;
  calculatorState.showVersionHistory = false;
  calculatorState.recoverySnapshots = saveCalculatorRecoverySnapshot(calculatorState, activeBackendRevision, 'restored');
  hasLocalDraft = true;
  validateCalculatorState(calculatorState);
  saveCalculatorDraft(calculatorState, activeBackendRevision);
  rerender();
  return true;
}

function clearCalculatorRecoverySnapshots() {
  try {
    window.localStorage.removeItem(calculatorRecoveryStorageKey());
  } catch (_error) {
    // No-op.
  }
  if (calculatorState) calculatorState.recoverySnapshots = [];
}
