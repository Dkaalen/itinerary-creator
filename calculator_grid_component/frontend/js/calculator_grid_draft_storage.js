let calculatorDraftStorageKey = 'itineraryCalculatorBrowserDraft.v3.global';
const CALCULATOR_DRAFT_STORAGE_PREFIX = 'itineraryCalculatorBrowserDraft.v3.';
const CALCULATOR_DRAFT_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 30;
const CALCULATOR_RECOVERY_SCHEMA_VERSION = 4;
const CALCULATOR_RECOVERY_MAX_SNAPSHOTS = 20;
const CALCULATOR_RECOVERY_STORAGE_BUDGET_BYTES = 4 * 1024 * 1024;
const calculatorStorageWarnings = {draft: '', recovery: ''};
let calculatorLocalRecoveryPaused = false;

function setCalculatorDraftStorageKey(key) {
  const value = String(key || '').trim();
  const nextKey = value || 'itineraryCalculatorBrowserDraft.v3.global';
  if (nextKey !== calculatorDraftStorageKey) {
    calculatorStorageWarnings.draft = '';
    calculatorStorageWarnings.recovery = '';
    calculatorLocalRecoveryPaused = false;
  }
  calculatorDraftStorageKey = nextKey;
  cleanupObsoleteCalculatorRecoveryNamespaces();
  return calculatorDraftStorageKey;
}

function getCalculatorDraftStorageKey() {
  return calculatorDraftStorageKey;
}

function calculatorRecoveryStorageKey(baseKey = calculatorDraftStorageKey) {
  return `${baseKey}.versions`;
}

function calculatorStorageStatusPayload() {
  const unavailable = Boolean(calculatorStorageWarnings.draft);
  const reduced = !unavailable && Boolean(calculatorStorageWarnings.recovery);
  if (unavailable) {
    return {
      state: 'unavailable',
      summary: 'Local recovery unavailable',
      detail: calculatorStorageWarnings.draft,
    };
  }
  if (reduced) {
    return {
      state: 'reduced',
      summary: 'Local recovery reduced',
      detail: calculatorStorageWarnings.recovery,
    };
  }
  return {
    state: 'available',
    summary: 'Local recovery ready',
    detail: 'The current Calculator draft and recent recovery versions can be stored in this browser.',
  };
}

function calculatorStorageWarningMessage() {
  const status = calculatorStorageStatusPayload();
  return status.state === 'available' ? '' : status.summary;
}

function setCalculatorStorageWarning(kind, message) {
  if (!(kind in calculatorStorageWarnings)) return;
  const previous = JSON.stringify(calculatorStorageStatusPayload());
  calculatorStorageWarnings[kind] = String(message || '');
  const currentStatus = calculatorStorageStatusPayload();
  const current = JSON.stringify(currentStatus);
  if (calculatorState) {
    calculatorState.recoveryStatus = currentStatus;
    calculatorState.recoveryWarning = currentStatus.state === 'available' ? '' : currentStatus.summary;
  }
  if (previous !== current && typeof refreshRecoveryStatusOnly === 'function') {
    refreshRecoveryStatusOnly();
  }
}

function calculatorRecognizedDraftBaseKey(key) {
  const value = String(key || '');
  if (!value.startsWith(CALCULATOR_DRAFT_STORAGE_PREFIX)) return '';
  return value.endsWith('.versions') ? value.slice(0, -'.versions'.length) : value;
}

function calculatorStoredNamespaceKeys() {
  const namespaces = new Set();
  try {
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const baseKey = calculatorRecognizedDraftBaseKey(window.localStorage.key(index));
      if (baseKey) namespaces.add(baseKey);
    }
  } catch (_error) {
    setCalculatorStorageWarning('draft', 'This browser cannot access local recovery storage right now. Calculator editing continues normally.');
  }
  return [...namespaces];
}

function calculatorStoredDraftSavedAt(raw) {
  try {
    const parsed = JSON.parse(String(raw || ''));
    return Number(parsed?.savedAt || 0);
  } catch (_error) {
    return 0;
  }
}

function calculatorStoredRecoverySavedAt(raw) {
  try {
    const parsed = JSON.parse(String(raw || ''));
    const entries = Array.isArray(parsed) ? parsed : parsed?.entries;
    if (!Array.isArray(entries)) return 0;
    return entries.reduce((latest, entry) => Math.max(latest, Number(entry?.savedAt || 0)), 0);
  } catch (_error) {
    return 0;
  }
}

function calculatorNamespaceLastSavedAt(baseKey) {
  try {
    return Math.max(
      calculatorStoredDraftSavedAt(window.localStorage.getItem(baseKey)),
      calculatorStoredRecoverySavedAt(window.localStorage.getItem(calculatorRecoveryStorageKey(baseKey)))
    );
  } catch (_error) {
    return 0;
  }
}

function cleanupObsoleteCalculatorRecoveryNamespaces(now = Date.now()) {
  const cutoff = Number(now || Date.now()) - CALCULATOR_DRAFT_MAX_AGE_MS;
  for (const baseKey of calculatorStoredNamespaceKeys()) {
    if (baseKey === calculatorDraftStorageKey) continue;
    const lastSavedAt = calculatorNamespaceLastSavedAt(baseKey);
    if (!lastSavedAt || lastSavedAt >= cutoff) continue;
    try {
      window.localStorage.removeItem(baseKey);
      window.localStorage.removeItem(calculatorRecoveryStorageKey(baseKey));
    } catch (_error) {
      setCalculatorStorageWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
      return;
    }
  }
}

function pruneOtherCalculatorRecoveryNamespacesForQuota() {
  const candidates = calculatorStoredNamespaceKeys()
    .filter((baseKey) => baseKey !== calculatorDraftStorageKey)
    .map((baseKey) => ({baseKey, savedAt: calculatorNamespaceLastSavedAt(baseKey)}))
    .sort((left, right) => left.savedAt - right.savedAt);
  let removed = 0;
  for (const candidate of candidates) {
    try {
      const recoveryKey = calculatorRecoveryStorageKey(candidate.baseKey);
      if (window.localStorage.getItem(recoveryKey) === null) continue;
      window.localStorage.removeItem(recoveryKey);
      removed += 1;
    } catch (_error) {
      break;
    }
  }
  return removed;
}

function calculatorUtf8Bytes(value) {
  const text = String(value || '');
  if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(text).length;
  return unescape(encodeURIComponent(text)).length;
}

function calculatorQuotaBytes(key, value) {
  const text = `${String(key || '')}${String(value || '')}`;
  return Math.max(calculatorUtf8Bytes(text), text.length * 2);
}

function calculatorStoredValue(key) {
  try {
    return window.localStorage.getItem(key) || '';
  } catch (_error) {
    return '';
  }
}

function calculatorRecoveryStorageUsage(draftRaw = null, recoveryRaw = null) {
  const resolvedDraft = draftRaw === null ? calculatorStoredValue(calculatorDraftStorageKey) : String(draftRaw || '');
  const resolvedRecovery = recoveryRaw === null ? calculatorStoredValue(calculatorRecoveryStorageKey()) : String(recoveryRaw || '');
  const draftBytes = calculatorUtf8Bytes(resolvedDraft);
  const recoveryBytes = calculatorUtf8Bytes(resolvedRecovery);
  return {
    draftBytes,
    recoveryBytes,
    totalBytes: draftBytes + recoveryBytes,
    quotaBytes: calculatorQuotaBytes(calculatorDraftStorageKey, resolvedDraft)
      + calculatorQuotaBytes(calculatorRecoveryStorageKey(), resolvedRecovery)
  };
}

function formatCalculatorStorageBytes(bytes) {
  const value = Math.max(0, Number(bytes || 0));
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(value < 10240 ? 1 : 0)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function calculatorStorageErrorIsQuota(error) {
  return Boolean(
    error
    && (
      error.name === 'QuotaExceededError'
      || error.name === 'NS_ERROR_DOM_QUOTA_REACHED'
      || Number(error.code) === 22
      || Number(error.code) === 1014
    )
  );
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
    setCalculatorStorageWarning('draft', 'This browser could not read the local recovery copy. Calculator editing continues normally.');
    return null;
  }
}

function calculatorDraftPayload(state, backendRevision) {
  return {
    schemaVersion: CALCULATOR_RECOVERY_SCHEMA_VERSION,
    rows: normalizeRowsForPython(state.rows),
    numberOfPax: state.numberOfPax ?? null,
    showAdvanced: Boolean(state.showAdvanced),
    selectedRowIndex: Number(state.selectedRowIndex || 0),
    activeCell: activeCell ? {...activeCell} : null,
    selection: state.selection ? {...state.selection} : null,
    columnWidths: {...(state.columnWidths || {})},
    backendRevision: String(backendRevision || ''),
    savedAt: Date.now()
  };
}

function saveCalculatorDraftAfterPruningActiveRecovery(serialized) {
  let snapshots = loadCalculatorRecoverySnapshots();
  while (snapshots.length) {
    snapshots = snapshots.slice(0, -1);
    try {
      if (snapshots.length) {
        window.localStorage.setItem(calculatorRecoveryStorageKey(), encodeCalculatorRecoverySnapshots(snapshots));
      } else {
        window.localStorage.removeItem(calculatorRecoveryStorageKey());
      }
      if (calculatorState) calculatorState.recoverySnapshots = snapshots;
      if (typeof refreshVersionHistoryCount === 'function') refreshVersionHistoryCount();
      window.localStorage.setItem(calculatorDraftStorageKey, serialized);
      return true;
    } catch (error) {
      if (!calculatorStorageErrorIsQuota(error)) return false;
    }
  }
  clearCalculatorRecoveryStorageOnly();
  try {
    window.localStorage.setItem(calculatorDraftStorageKey, serialized);
    return true;
  } catch (_error) {
    return false;
  }
}

function saveCalculatorDraft(state, backendRevision) {
  if (!state || !Array.isArray(state.rows)) return false;
  if (calculatorLocalRecoveryPaused) return true;
  const serialized = JSON.stringify(calculatorDraftPayload(state, backendRevision));
  pruneCalculatorRecoveryForDraft(serialized);
  try {
    window.localStorage.setItem(calculatorDraftStorageKey, serialized);
    setCalculatorStorageWarning('draft', '');
    updateCalculatorRecoveryStorageUsage();
    return true;
  } catch (error) {
    if (calculatorStorageErrorIsQuota(error)) {
      const otherRecoveryNamespacesRemoved = pruneOtherCalculatorRecoveryNamespacesForQuota();
      if (otherRecoveryNamespacesRemoved) {
        try {
          window.localStorage.setItem(calculatorDraftStorageKey, serialized);
          setCalculatorStorageWarning('draft', '');
          setCalculatorStorageWarning('recovery', 'Older local recovery versions from inactive projects were removed to protect the current Calculator draft.');
          updateCalculatorRecoveryStorageUsage();
          return true;
        } catch (_otherNamespaceRetryError) {
          // Continue by pruning the active project's older recovery versions.
        }
      }
      if (saveCalculatorDraftAfterPruningActiveRecovery(serialized)) {
        setCalculatorStorageWarning('draft', '');
        setCalculatorStorageWarning('recovery', 'Older local recovery versions were removed to protect the current Calculator draft.');
        updateCalculatorRecoveryStorageUsage();
        return true;
      }
    }
    setCalculatorStorageWarning('draft', 'This browser cannot store a local recovery copy right now. Calculator editing continues normally.');
    updateCalculatorRecoveryStorageUsage();
    return false;
  }
}

function clearCalculatorDraft() {
  try {
    window.localStorage.removeItem(calculatorDraftStorageKey);
    setCalculatorStorageWarning('draft', '');
  } catch (_error) {
    setCalculatorStorageWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
  }
  updateCalculatorRecoveryStorageUsage();
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
    if (ignored.has(key) || key.startsWith('_') || key.endsWith('_override')) continue;
    if (typeof value === 'boolean') {
      if (value) return true;
      continue;
    }
    if (value === null || value === undefined) continue;
    if (String(value).trim() !== '' && String(value).trim() !== '0') return true;
  }
  return false;
}

function calculatorRecoveryHash(value) {
  const text = String(value || '');
  let first = 0xdeadbeef ^ text.length;
  let second = 0x41c6ce57 ^ text.length;
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    first = Math.imul(first ^ code, 2654435761);
    second = Math.imul(second ^ code, 1597334677);
  }
  first = Math.imul(first ^ (first >>> 16), 2246822507) ^ Math.imul(second ^ (second >>> 13), 3266489909);
  second = Math.imul(second ^ (second >>> 16), 2246822507) ^ Math.imul(first ^ (first >>> 13), 3266489909);
  return `${(second >>> 0).toString(16).padStart(8, '0')}${(first >>> 0).toString(16).padStart(8, '0')}`;
}

function calculatorRecoveryComparable(snapshot) {
  return {
    rows: snapshot.rows,
    numberOfPax: snapshot.numberOfPax ?? null,
    showAdvanced: Boolean(snapshot.showAdvanced),
    columnWidths: {...(snapshot.columnWidths || {})}
  };
}

function calculatorRecoverySnapshot(state, backendRevision, reason) {
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
    reason: String(reason || 'edit')
  };
  snapshot.hash = calculatorRecoveryHash(JSON.stringify(calculatorRecoveryComparable(snapshot)));
  return snapshot;
}

function calculatorRecoverySnapshotLimit(snapshotBytes) {
  const size = Math.max(0, Number(snapshotBytes || 0));
  if (size <= 64 * 1024) return CALCULATOR_RECOVERY_MAX_SNAPSHOTS;
  if (size <= 192 * 1024) return 14;
  if (size <= 512 * 1024) return 8;
  if (size <= 1024 * 1024) return 4;
  return 2;
}

function calculatorRowsDelta(baseRows, targetRows) {
  const source = Array.isArray(baseRows) ? baseRows : [];
  const target = Array.isArray(targetRows) ? targetRows : [];
  const changes = [];
  for (let index = 0; index < target.length; index += 1) {
    const sourceRow = source[index];
    const targetRow = target[index];
    if (JSON.stringify(sourceRow) !== JSON.stringify(targetRow)) changes.push([index, targetRow]);
  }
  return {rowCount: target.length, rowChanges: changes};
}

function applyCalculatorRowsDelta(baseRows, entry) {
  const rowCount = Math.max(0, Number(entry.rowCount || 0));
  const rows = cloneRows(baseRows).slice(0, rowCount);
  while (rows.length < rowCount) rows.push({});
  for (const change of entry.rowChanges || []) {
    if (!Array.isArray(change) || change.length !== 2) continue;
    const index = Number(change[0]);
    if (!Number.isInteger(index) || index < 0 || index >= rowCount) continue;
    rows[index] = {...(change[1] || {})};
  }
  return rows;
}

function calculatorRecoveryMetadata(snapshot) {
  return {
    id: String(snapshot.id || ''),
    numberOfPax: snapshot.numberOfPax ?? null,
    showAdvanced: Boolean(snapshot.showAdvanced),
    selectedRowIndex: Number(snapshot.selectedRowIndex || 0),
    activeCell: snapshot.activeCell ? {...snapshot.activeCell} : null,
    selection: snapshot.selection ? {...snapshot.selection} : null,
    columnWidths: {...(snapshot.columnWidths || {})},
    backendRevision: String(snapshot.backendRevision || ''),
    savedAt: Number(snapshot.savedAt || 0),
    reason: String(snapshot.reason || 'edit'),
    hash: String(snapshot.hash || calculatorRecoveryHash(JSON.stringify(calculatorRecoveryComparable(snapshot))))
  };
}

function encodeCalculatorRecoverySnapshots(snapshots) {
  const entries = [];
  let newerSnapshot = null;
  for (const snapshot of snapshots || []) {
    const metadata = calculatorRecoveryMetadata(snapshot);
    if (!newerSnapshot) {
      entries.push({...metadata, kind: 'full', rows: snapshot.rows});
      newerSnapshot = snapshot;
      continue;
    }
    const delta = calculatorRowsDelta(newerSnapshot.rows, snapshot.rows);
    const deltaEntry = {...metadata, kind: 'delta', ...delta};
    const fullEntry = {...metadata, kind: 'full', rows: snapshot.rows};
    entries.push(JSON.stringify(deltaEntry).length < JSON.stringify(fullEntry).length ? deltaEntry : fullEntry);
    newerSnapshot = snapshot;
  }
  return JSON.stringify({schemaVersion: CALCULATOR_RECOVERY_SCHEMA_VERSION, entries});
}

function decodeCalculatorRecoveryPayload(parsed) {
  if (Array.isArray(parsed)) {
    return parsed.map((snapshot) => ({
      ...snapshot,
      rows: cloneRows(snapshot?.rows || []),
      hash: String(snapshot?.hash || calculatorRecoveryHash(JSON.stringify(calculatorRecoveryComparable(snapshot || {}))))
    }));
  }
  if (!parsed || Number(parsed.schemaVersion) !== CALCULATOR_RECOVERY_SCHEMA_VERSION || !Array.isArray(parsed.entries)) return [];
  const snapshots = [];
  let newerRows = [];
  for (const entry of parsed.entries) {
    if (!entry || !entry.id) continue;
    let rows;
    if (entry.kind === 'full' && Array.isArray(entry.rows)) {
      rows = cloneRows(entry.rows);
    } else if (entry.kind === 'delta' && snapshots.length) {
      rows = applyCalculatorRowsDelta(newerRows, entry);
    } else {
      continue;
    }
    const snapshot = {...calculatorRecoveryMetadata({...entry, rows}), rows};
    snapshots.push(snapshot);
    newerRows = rows;
  }
  return snapshots;
}

function readCalculatorRecoverySnapshots() {
  const raw = window.localStorage.getItem(calculatorRecoveryStorageKey());
  if (!raw) return [];
  return decodeCalculatorRecoveryPayload(JSON.parse(raw));
}

function loadCalculatorRecoverySnapshots() {
  try {
    const cutoff = Date.now() - CALCULATOR_DRAFT_MAX_AGE_MS;
    return readCalculatorRecoverySnapshots()
      .filter((snapshot) => snapshot && Array.isArray(snapshot.rows) && Number(snapshot.savedAt || 0) >= cutoff)
      .slice(0, CALCULATOR_RECOVERY_MAX_SNAPSHOTS);
  } catch (_error) {
    setCalculatorStorageWarning('recovery', 'Recent local recovery versions could not be read and will be rebuilt from the current draft.');
    return [];
  }
}

function calculatorRecoverySerializedWithinBudget(snapshots, draftRaw = null) {
  let retained = [...(snapshots || [])];
  let serialized = encodeCalculatorRecoverySnapshots(retained);
  while (
    retained.length
    && calculatorRecoveryStorageUsage(draftRaw, serialized).quotaBytes > CALCULATOR_RECOVERY_STORAGE_BUDGET_BYTES
  ) {
    retained = retained.slice(0, -1);
    serialized = encodeCalculatorRecoverySnapshots(retained);
  }
  return {snapshots: retained, serialized};
}

function writeCalculatorRecoverySnapshots(snapshots, draftRaw = null) {
  let candidate = calculatorRecoverySerializedWithinBudget(snapshots, draftRaw);
  while (candidate.snapshots.length) {
    try {
      window.localStorage.setItem(calculatorRecoveryStorageKey(), candidate.serialized);
      setCalculatorStorageWarning('recovery', candidate.snapshots.length < snapshots.length
        ? 'Older local recovery versions were removed to stay within browser storage limits.'
        : '');
      updateCalculatorRecoveryStorageUsage();
      return candidate.snapshots;
    } catch (error) {
      if (!calculatorStorageErrorIsQuota(error)) break;
      candidate = calculatorRecoverySerializedWithinBudget(candidate.snapshots.slice(0, -1), draftRaw);
    }
  }
  clearCalculatorRecoveryStorageOnly();
  setCalculatorStorageWarning('recovery', 'Older local recovery versions could not be kept. The current Calculator draft remains the priority.');
  updateCalculatorRecoveryStorageUsage();
  return [];
}

function pruneCalculatorRecoveryForDraft(draftRaw) {
  let snapshots;
  try {
    snapshots = loadCalculatorRecoverySnapshots();
  } catch (_error) {
    snapshots = [];
  }
  if (!snapshots.length) return;
  const candidate = calculatorRecoverySerializedWithinBudget(snapshots, draftRaw);
  if (candidate.snapshots.length === snapshots.length) return;
  const retained = writeCalculatorRecoverySnapshots(candidate.snapshots, draftRaw);
  if (retained.length < snapshots.length) {
    setCalculatorStorageWarning('recovery', 'Older local recovery versions were removed to protect the current Calculator draft.');
  }
}

function saveCalculatorRecoverySnapshot(state, backendRevision, reason = 'edit') {
  if (!state || !Array.isArray(state.rows) || calculatorLocalRecoveryPaused) return [];
  const snapshots = loadCalculatorRecoverySnapshots();
  const snapshot = calculatorRecoverySnapshot(state, backendRevision, reason);
  if (snapshots[0]?.hash === snapshot.hash) return snapshots;
  const fullSnapshotBytes = calculatorUtf8Bytes(JSON.stringify(snapshot));
  const retentionLimit = calculatorRecoverySnapshotLimit(fullSnapshotBytes);
  const updated = [snapshot, ...snapshots].slice(0, retentionLimit);
  return writeCalculatorRecoverySnapshots(updated);
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

function cancelCalculatorPendingRecoveryWrites({includeDraft = false} = {}) {
  if (includeDraft && typeof localDraftSaveTimer !== 'undefined') {
    window.clearTimeout(localDraftSaveTimer);
    localDraftSaveTimer = null;
  }
  if (typeof recoverySnapshotTimer !== 'undefined') {
    window.clearTimeout(recoverySnapshotTimer);
    recoverySnapshotTimer = null;
  }
}

function clearCalculatorRecoveryStorageOnly() {
  try {
    window.localStorage.removeItem(calculatorRecoveryStorageKey());
  } catch (_error) {
    // The visible warning is set by the caller.
  }
  if (calculatorState) calculatorState.recoverySnapshots = [];
  if (typeof refreshVersionHistoryCount === 'function') refreshVersionHistoryCount();
}

function clearCalculatorRecoverySnapshots() {
  cancelCalculatorPendingRecoveryWrites();
  clearCalculatorRecoveryStorageOnly();
  setCalculatorStorageWarning('recovery', '');
  if (calculatorState) calculatorState.recoverySnapshots = [];
  updateCalculatorRecoveryStorageUsage();
}


function clearCalculatorLocalRecoveryData() {
  cancelCalculatorPendingRecoveryWrites({includeDraft: true});
  try {
    window.localStorage.removeItem(calculatorDraftStorageKey);
    window.localStorage.removeItem(calculatorRecoveryStorageKey());
    calculatorStorageWarnings.draft = '';
    calculatorStorageWarnings.recovery = '';
    calculatorLocalRecoveryPaused = true;
    if (calculatorState) {
      calculatorState.recoverySnapshots = [];
      calculatorState.recoveryStatus = calculatorStorageStatusPayload();
      calculatorState.recoveryWarning = '';
    }
    updateCalculatorRecoveryStorageUsage();
    return true;
  } catch (_error) {
    setCalculatorStorageWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
    updateCalculatorRecoveryStorageUsage();
    return false;
  }
}

function updateCalculatorRecoveryStorageUsage() {
  if (calculatorState) calculatorState.recoveryStorageBytes = calculatorRecoveryStorageUsage().totalBytes;
}
